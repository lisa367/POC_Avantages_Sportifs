import sys
import requests
import logging
import time
import pandas as pd
from datetime import datetime as dt
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert
from geopy.distance import geodesic
from pathlib import Path

from models import employees_table, employees_activity_table


COMPANY_ADDRESS = "1362 avenue des Platanes, 34970 Lattes"
etl_logger = logging.getLogger("ETLHr_logger")
etl_logger.setLevel(logging.DEBUG)
etl_logger.addHandler(logging.StreamHandler(sys.stdout))


class ETLHr:
    """
    ETL Pipeline to ingest HR raw data into HR database.
    Runs everyday.
    """
    def __init__(self, data_path, company_address) -> None:
        self.data_path =  data_path
        self.company_address = company_address
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.osrm_url = "https://router.project-osrm.org/route/v1/walking/{longitude_1},{latitude_1};{longitude_2},{latitude_2}?overview=false"
        self.query_params = {'q': '{address}', 'format': 'json', 'limit': 1}
        self.query_headers = {"User-Agent": "MyApp/1.0 (myapp@gmail.com)"}
        self.company_geoloc = self.fetch_company_geoloc()
        self.engine = create_engine("postgresql:///sport_data_solutions.db", echo=True)
        self.session_class = sessionmaker(bind=self.engine)
        self.inspector = inspect(self.engine)

    def extract(self) -> dict[str, pd.DataFrame]:
        etl_logger.info("Extracting data")
        return {
            "hr_data": pd.read_excel(f"{self.data_path}/donnees_rh.xlsx").assign(commute_distance=0),
            "activity_data": pd.read_excel(f"{self.data_path}/donnees_sportives.xlsx")
        } 

    def transform(self, data_dict) -> dict[str, pd.DataFrame]:
        """Google Maps api pour le calcul des distances domicile-travail"""
        etl_logger.info("Transforming data")
        hr_data = (
            data_dict["hr_data"]
            .rename({
                "ID salarié": "employee_id",
                "Nom": "lastname",
                "Prénom": "firstname",
                "BU": "department",
                "Date d'embauche": "hiring_date",
                "Type de contrat": "contract_type",
                "Salaire brut": "salary",
                "Nombre de jours de CP": "pto_days",
                "Adresse du domicile": "address",
                "Moyen de déplacement": "commute_type",
            }, 
            axis=1)
            .astype({"employee_id": "int"})
            # .apply(self.get_commute_distance, axis=1)
        )
        hr_data["commute_distance"], hr_data["commute_duration"] = hr_data.apply(
            lambda x: pd.Series(self.get_commute_distance(x)), 
            axis=1
        )

        activity_data = (
            data_dict["activity_data"]
            .rename({
                "ID salarié": "employee_id",
                "Pratique d'un sport": "sport_type"
            }, 
            axis=1)
            .astype({"employee_id": "int"})
            .merge(
                hr_data[["employee_id", "commute_type", "commute_distance", "commute_duration"]],
                on="employee_id",
                how="left"
            )
        )
        # activity_data["strava_user_id"] = activity_data.apply(self.generate_strava_user_id, axis=1)
        activity_data["strava_user_id"] = activity_data.apply(lambda x: f"su_{x.employee_id}", axis=1)

        return {
            "employees": hr_data[[
                "employee_id",
                "firstname",
                "lastname",
                "address",
                "hiring_date",
                "department",
                "contract_type",
                "salary",
                "pto_days",
                ]].rename({"employee_id": "id"}, axis=1),
    
            "employees_activity": activity_data
        }
    
    def test_transform(self, data_dict: dict[str, pd.DataFrame]):
        df = data_dict["employees_activity"]
        df.apply(self.test_coherence_distance, axis=1)

    def load(self, dfs_dict) -> bool:
        etl_logger.info("Loading data")
        result = True
        tables = {
            "employees": employees_table,
            "employees_activity": employees_activity_table
        }
        for table_name, df in dfs_dict.items():
            etl_logger.info(f"Loading data into {table_name} table")
            pk_list = [pk.name for pk in table_name.primary_key.columns]
            with self.session_class() as session:
                if not self.inspector.has_table(table_name):
                    try:
                        tables[table_name].create(self.engine, checkfirst=True)
                        session.commit()
                        etl_logger.info(f"Successfully created {table_name} table")
                    except SQLAlchemyError as err:
                        result = False
                        session.rollback()
                        etl_logger.error(str(err))
                stmt = insert(tables[table_name]).values(df.to_dict(orient="records"))
                stmt = stmt.on_conflict_do_update(
                    index_elements=pk_list,
                    set_={x: stmt.excluded.get(x) for x in df.columns}
                )
                session.commit()

                session.close()

        return result

    def fetch_company_geoloc(self) -> tuple:
        query_params = self.query_params
        query_params["q"] = query_params["q"].format(address = self.company_address)
        res = requests.get(self.nominatim_url, params=query_params, headers=self.query_headers)
        if res.status_code != 200:
            raise Exception(f"NominatimError:\nProblem when trying to get compagny geoloc\n{res.status_code}\n{res.content}")
        
        # Return (latitude, longitude) tuple
        return (float(res.json()[0]["lat"]), float(res.json()[0]["lon"]))

    def get_commute_distance(self, x):
        """Get geoloc with Nominatim API. Then get distance with OSRM API"""
        query_params = self.query_params
        query_params["q"] = query_params["q"].format(address = x.address)
        res = requests.get(self.nominatim_url, params=query_params, headers=self.query_headers)
        if res.status_code != 200:
            raise Exception(f"NominatimError:\nProblem when trying to get employee's address geoloc\n{res.status_code}\n{res.content}")
        
        # Set (latitude, longitude) tuple
        employee_geoloc = (float(res.json()[0]["lat"]), float(res.json()[0]["lon"]))
        res_osrm = requests.get(self.osrm_url.format(
            longitude_1 = self.company_geoloc[1],
            latitude_1 = self.company_geoloc[0],
            longitude_2 = employee_geoloc[1],
            latitude_2 = employee_geoloc[0],
            )).json()
        
        if res_osrm.status_code != 200:
            return round(geodesic(self.company_geoloc, employee_geoloc).km), 1800

        return round(res_osrm["routes"][0]["legs"][0]["distance"] / 1000), round(res_osrm.json()["routes"][0]["legs"][0]["duration"])

    def test_coherence_distance(self, x):
        if x.distance < 0:
            raise Exception(f"CommuteDistanceError : distance cannot be negative - ({x.employee_id}, {x.commute_distance})")
        if x.commute_type == "Marche/running" and x.distance > 15:
            raise Exception(f"CommuteDistanceError : distance doesn't match commute_type 'Marche/running' - ({x.employee_id}, {x.commute_distance})")
        if x.commute_type == "Vélo/Trottinette/Autres" and x.distance > 25:
            raise Exception(f"CommuteDistanceError : distance doesn't match commute_type 'Vélo/Trottinette/Autres' - ({x.employee_id}, {x.commute_distance})")
        
        return x


    def run(self, test_mode=True):
        start = time.time()
        etl_logger.info(f"ETLHr starts at {dt.now()}")

        raw_data = self.extract()
        transformed_data = self.transform(raw_data)
        self.test_transform(transformed_data)
        self.load(transformed_data)

        etl_logger.info(f"ETLHr ends at {dt.now()}")
        end = time.time()
        etl_logger.info(f"Task duration : {end - start} seconds.")
    

if __name__ == "__main__":
    raw_data_path = Path().cwd()/"data"
    print(f"Importing raw data from : {raw_data_path}")
    etl = ETLHr(raw_data_path, COMPANY_ADDRESS)
    etl.run()
