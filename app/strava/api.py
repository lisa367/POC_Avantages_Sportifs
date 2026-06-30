import os
from dotenv import load_dotenv
from datetime import datetime as dt, timedelta
from fastapi import FastAPI, APIRouter, HTTPException
from pymongo import MongoClient
from models import Activity


load_dotenv()

client = MongoClient(os.environ.get("MONGO_URI", "mongodb://mongo_api:27017"))
db = client["strava_history"]
activities_collection = db["activities"]


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
