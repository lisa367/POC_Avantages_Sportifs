import os
import sys
import logging
import random
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from pymongo import MongoClient
from pydantic import BaseModel

INIT_MODE = True if os.environ.get("INIT") == "True" else False


strava_db_logger = logging.getLogger("StravaDbLogger")
strava_db_logger.setLevel(logging.DEBUG)
strava_db_logger.addHandler(logging.StreamHandler(sys.stdout))


class Activity(BaseModel):
    user_id: str
    updated_at: datetime
    activity_name: str 
    activity_type: str 
    sport_type: str 
    start_date_local: datetime 
    elapsed_time: int
    distance: float 
    trainer: int 
    commute: int

class StravaHistory:
    def __init__(self, start_date, end_date) -> None:
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.psql_engine = create_engine("postgresql:///sport_data_solutions.db", echo=True)
        self.mongo_client = MongoClient(os.environ.get("MONGO_URI", "mongodb://mongo_api:27017"))
        self.activities_collection = self.mongo_client["strava_history"]["activities"]

    def daterange(self):

        current = self.start_date

        while current <= self.end_date:
            yield current
            current += timedelta(days=1)


    def get_commuting_employees(self):
        query = \
            """
            SELECT strava_user_id, commute_distance, commute_duration 
            FROM strava.employees_activity 
            WHERE LOWER(commute_type) IN ('marche/running', 'vélo/trottinette/autres')
            """
        with self.psql_engine.connect() as con:
            result = con.execute(text(query))

        return [
                {
                    "user_id": row.strava_user_id,
                    "distance": float(row.commute_distance),
                    "duration": float(row.commute_duration)
                }
                for row in result
            ]

    def get_exercising_employees(self):
        query = \
            """
            SELECT strava_user_id, sport_name
            FROM strava.employees_activity 
            WHERE sport_type IS NOT NULL
            """
        with self.psql_engine.connect() as con:
            result = con.execute(text(query))
        
        return [
                {
                    "user_id": row.strava_user_id,
                    "sport": row.sport_name
                }
                for row in result
            ]

    def create_commute_activity_history(self):
        employees = self.get_exercising_employees()
        new_data = []
        for day in self.daterange():
            if day.weekday() >= 5:
                continue
          
            for employee in employees:
                # environ 3 trajets par semaine
                if random.random() > 0.60:
                    continue

                activity = Activity(
                    user_id=employee["user_id"],
                    updated_at=datetime.now(),
                    activity_name="Trajet domicile-travail",
                    activity_type="Course/marche",
                    sport_type="Marche/Running",
                    start_date_local=day.isoformat(),
                    elapsed_time=employee["duration"],
                    distance=employee["distance"],
                    trainer=0,
                    commute=1
                )

                new_data.append(activity.model_dump())

        return new_data


    def create_exercise_activity_history(self):
        emloyees_info = self.get_exercising_employees()
        new_data = []

        for day in self.daterange():

            # une activité sportive par semaine
            if day.weekday() != 6:
                continue

            for employee in emloyees_info:

                activity = Activity(
                    user_id=employee["user_id"],
                    updated_at=datetime.now(),
                    activity_name=f"Séance de {employee['sport']}",
                    activity_type=employee["sport"],
                    sport_type=employee["sport"],
                    start_date_local=day.isoformat(),
                    elapsed_time=random.randint(900, 3600),
                    distance=round(random.uniform(5, 25), 2),
                    trainer=1,
                    commute=0
                )

                new_data.append(activity.model_dump())

        return new_data


    def populate_db(self, inspect_mode=True):
        commute_data = self.create_commute_activity_history()
        exercise_data = self.create_exercise_activity_history()

        all_data = commute_data + exercise_data

        if not inspect_mode:
            if all_data:
                self.activities_collection.insert_many(all_data)

            strava_db_logger.info(
                f"{len(all_data)} documents insérés dans la collection activities."
            )
        else:
            for data in all_data:
                print(data, sep="\n")


if __name__ == "__main__" and INIT_MODE:
    historique = StravaHistory("2026-06-01", "2026-06-30")
    historique.populate_db()
