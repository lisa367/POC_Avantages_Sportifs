import os
import sys
import requests
import logging
import time
from datetime import datetime as dt, timedelta
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from models import users_activities_table

etl_logger = logging.getLogger("ETLSlack")
etl_logger.setLevel(logging.DEBUG)
etl_logger.addHandler(logging.StreamHandler(sys.stdout))


class ETLSlack:
    def __init__(self, execution_date) -> None:
        self.slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        self.slack_channel = os.environ["SLACK_CHANNEL"]
        self.psql_engine = create_engine("postgresql:///sport_data_solutions.db", echo=True)
        self.session_class = sessionmaker(bind=self.psql_engine)
        self.inspector = inspect(self.psql_engine)
        self.strava_url = "http://127.0.0.1:8000"
        self.date = execution_date.strftime("%Y-%m-%d")

    def get_users(self):
        query = \
            """
            SELECT employee_id, strava_user_id, firstname, lastname
            FROM hr.employees_activity ea
            JOIN hr.employees a ON ea.employee_id = e.id
            WHERE sport_type IS NOT NULL
            """
        with self.psql_engine.connect() as con:
            result = con.execute(text(query))
        
        return [
                {
                    "user_id": row.strava_user_id,
                    "employee_id": row.employee_id,
                    "firstname": row.firstname,
                    "lastname": row.lastname
                }
                for row in result
            ]

    def get_users_daily_activities(self, users):
        users_activities = []
        for user in users:
            response = requests.get(f"{self.strava_url}/{user['user_id']}/{self.date}")
            # print(response)
            if response.status_code == 200:
                # users_activities[employee_id] = response.json()
                for item in response.json():
                    item["employee_id"] = user["employee_id"]
                    item["row_udated_at"] = self.date
                    users_activities.append(item)
            # else:
            #     users_activities[employee_id] = []
        return users_activities
    
    def get_user_total_activities(self, user):
        response = requests.get(f"{self.strava_url}/user/{user['user_id']}")

        if response.status_code == 200:
            return response.json()

        return []

    def send_slack_messages(self, users, activities, demo=True):
        names = {u.employee_id : {u.firstname, u.lastname} for u in users}
        for employee_id, employee_activities in activities.items():
            # employee = [u for u in users if u["employee_id"] == employee_id][0]
            message = (
                    f"🏃 Activités du {self.date}\n\n"
                )

            for activity in employee_activities:

                message += (
                    f"• {activity['activity_name']}\n"
                    f"  Distance : {activity['distance']} km\n"
                    f"  Temps : {activity['elapsed_time']//60} min\n\n"
                    f"Bravo {names[employee_id]["firstname"]} {names[employee_id]["lastname"]}! 🎉"
                )
            try:
                self.slack_client.chat_postMessage(
                    channel=self.slack_channel,
                    text=message
                )
            except SlackApiError as err:
                etl_logger.warning(err)

    def load(self, data_to_insert) -> bool:
        result = True

        etl_logger.info(f"Loading data into users_activities table")
        with self.session_class() as session:
            if not self.inspector.has_table("users_activities"):
                try:
                    users_activities_table.create(self.psql_engine, checkfirst=True)
                    session.commit()
                    etl_logger.info(f"Successfully created users_activities table")
                except SQLAlchemyError as err:
                    result = False
                    session.rollback()
                    etl_logger.error(str(err))
            stmt = insert(users_activities_table).values(data_to_insert)
            session.execute(stmt)
            session.commit()

            session.close()

        return result

    def run(self):
        start = time.time()
        etl_logger.info(f"ETLSlack starts at {dt.now()}")
        users = self.get_users()
        activities = self.get_users_daily_activities(users)
        self.send_slack_messages(users, activities)
        self.load(activities)
        etl_logger.info(f"ETLSlack ends at {dt.now()}")
        end = time.time()
        etl_logger.info(f"Task duration : {end - start} seconds.")
        return


if __name__ == "__main__":
    execution_date = dt.now() - timedelta(days=1)
    etl_slack = ETLSlack(execution_date)
    etl_slack.run()
