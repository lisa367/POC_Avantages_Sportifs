import os
import sys
import time
import logging
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime as dt
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert

from models import primes_sportives_table


load_dotenv()

POSTGRES_URI = os.environ.get("POSTGRES_URI", "postgresql:///sport_data_solutions.db")

etl_logger = logging.getLogger("ETLCalculPrimes")
etl_logger.setLevel(logging.DEBUG)
etl_logger.addHandler(logging.StreamHandler(sys.stdout))


class ETLCalculPrimes:
    def __init__(self, execution_date) -> None:
        self.psql_engine = create_engine(POSTGRES_URI, echo=True)
        self.session_class = sessionmaker(bind=self.psql_engine)
        self.inspector = inspect(self.psql_engine)
        self.date = execution_date.strftime("%Y-%m-%d")

    def extract(self):
        etl_logger.info("Extracting data")
        query_hr = \
            """
            SELECT id AS employee_id, salary
            FROM hr.employees
            """
        query_commute = \
            """
            SELECT employee_id, (commute_type IN ('Marche/running', 'Vélo/Trottinette/Autres')) AS is_active_commuter
            FROM hr.employees_activity
            """
        query_strava = \
            """
            SELECT employee_id, COUNT(*) AS num_seances_sports
            FROM strava_api.users_activities
            WHERE trainer = 1
            GROUP BY employee_id
            """
        with self.psql_engine.connect() as con:
            result_hr= con.execute(text(query_hr))
            result_commute = con.execute(text(query_commute))
            result_strava = con.execute(text(query_strava))
        
        return {
                    "hr_data": pd.DataFrame([{"employee_id": row.employee_id, "salary": row.salary} for row in result_hr]),
                    "commuting_data": pd.DataFrame([{"employee_id": row.employee_id, "is_active_commuter": row.is_active_commuter} for row in result_commute]),
                    "strava_api_data": pd.DataFrame([{"employee_id": row.employee_id,} for row in result_strava])
                }


    def transform(self, data_dict):
        etl_logger.info("Transforming data")
        merged_data = (
            data_dict["hr_data"]
            .merge(data_dict["commuting_data"], on="employee_id", how="left")
            .merge(data_dict["strava_api_data"], on="employee_id", how="left")
        )
        merged_data["row_updated_at"] = self.date
        return merged_data


    def load(self, dfs_dict) -> bool:
        etl_logger.info("Loading data")
        result = True

        etl_logger.info(f"Loading data into users_activities table")
        with self.session_class() as session:
            if not self.inspector.has_table("users_activities"):
                try:
                    primes_sportives_table.create(self.psql_engine, checkfirst=True)
                    session.commit()
                    etl_logger.info(f"Successfully created users_activities table")
                except SQLAlchemyError as err:
                    result = False
                    session.rollback()
                    etl_logger.error(str(err))
            stmt = insert(primes_sportives_table).values(dfs_dict.to_dict(orient="records.q/"))
            stmt = stmt.on_conflict_do_update(
                    index_elements={"employee_id"},
                    set_={x: stmt.excluded.get(str(x)) for x in primes_sportives_table.columns}
                )
            session.execute(stmt)
            session.commit()

            session.close()

        return result

    def run(self):
        start = time.time()
        etl_logger.info(f"ETLCalculPrimes starts at {dt.now()}")
        raw_data = self.extract()
        transformed_data = self.transform(raw_data)
        self.load(transformed_data)
        etl_logger.info(f"ETLCalculPrimes ends at {dt.now()}")
        end = time.time()
        etl_logger.info(f"Task duration : {end - start} seconds.")
        return


if __name__ == "__main__":
    execution_date = dt.now()
    etl_slack = ETLCalculPrimes(execution_date)
    etl_slack.run()
