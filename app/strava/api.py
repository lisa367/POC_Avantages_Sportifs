import os
from datetime import datetime as dt, timedelta
# from flask import Flask
from fastapi import FastAPI, APIRouter, HTTPException
from pymongo import MongoClient
from models import Activity

client = MongoClient(os.environ.get("MONGO_URI", "mongodb://mongo_api:27017"))
db = client["strava_history"]
activities_collection = db["activities"]

# recuperer la liste les employee_id dans la table employees
# generer un strava user_id pour chq employé et remplir la table employees_strava [employee_id, strava_user_id, commuting_type/method, exercising_type]
# generer une ligne strava depuis 2025, pour chq employé qui vient en marchant/courant, pour 3 jours de la semaine (entre lundi et vendredi)
# generer une ligne strava depuis 2025, pour chq employé qui a une activité sportive, pour 3 jours de la semaine (entre lundi et dimanche)

# distance in meters, elapsed_time in seconds, total_elevation_gain in meters
# {"user_id": 123456, "activities": [{"name": "Run", "type": "Run",  "sport_type": "Run", "start_date_local": "2024-06-01T06:00:00Z", "elapsed_time": 1600, "distance": 5000, "trainer": 0, "commute": 1]}
# API_RESPONSE = ["name" "type",  "sport_type", "start_date_local", "elapsed_time", "distance", "trainer", "commute"]

api_response_template = {
    "id": '',
    "user_id": '',
    "activities": [
        {
            "activity_name", "activity_type", "sport_type", "start_date_local", "elapsed_time", "distance", "trainer", "commute"
        }
    ],
}

api = FastAPI(title="Strava History API")
router = APIRouter(prefix="/activity", tags=["Activities"])

api.include_router(router)

def individual_serializer(activity):
    return {
        "id": str(activity["_id"]),
        "user_id": activity["user_id"],
        "activity_name": activity["activity_name"],
        "activity_type": activity["activity_type"],
        "sport_type": activity["sport_type"],
        "start_date_local": activity["start_date_local"],
        "elapsed_time": activity["elapsed_time"],
        "distance": activity["distance"],
        "trainer": activity["trainer"],
        "commute": activity["commute"],
    }


def list_serializer(activities):
    return [individual_serializer(activity) for activity in activities]

@router.get("/")
async def index():
    return "The api is up and running :)"


@router.get("/user/{user_id}")
async def get_user_activities(user_id:int):
    activities = activities_collection.find(
        {"user_id": user_id}
    )
    return list_serializer(activities)


@router.get("/user/{user_id}/{date}")
async def get_daily_activities(user_id: str, date:str):
    try:
        target_day = dt.strptime(date, "%Y-%m-%d")

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Date must be in YYYY-MM-DD format."
        )

    # next_day = target_day + timedelta(days=1)

    activities = activities_collection.find(
        {
            "user_id": user_id,
            "start_date_local": {
                "$gte": target_day.isoformat(),
                "$lt": target_day + timedelta(days=1) # next_day.isoformat()
            }
        }
    )

    return list_serializer(activities)

api.include_router(router)

# uvicorn api:api --reload


# api = Flask(__name__)


# @api.route("/strava")
# def index():
#     return "The api is up and running :)"


# @api.route("/activity/{int:user_id}", methods=["GET"])
# def get_activity_data():
#     return ''
