from sqlalchemy import MetaData, Table, Column, String, Integer, Float, DateTime

meta = MetaData()


users_activities_table = Table(
    "users_activities",
    meta,
    Column("employee_id", Integer),
    Column("activity_id", String),
    Column("user_id", String),
    Column("activity_name", String),
    Column("activity_type", String),
    Column("sport_type", String),
    Column("start_date_local", String),
    Column("elapsed_time", Integer),
    Column("trainer", Integer),
    Column("commute", Integer),
    Column("row_updated_at", DateTime),

    schema="strava_api"
)