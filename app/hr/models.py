from sqlalchemy import MetaData, Table, Column, String, Integer, Float, ForeignKey, UniqueConstraint

meta = MetaData()


employees_table = Table(
    "employees",
    meta,
    Column("id", Integer, primary_key=True),
    Column("firstname", String),
    Column("lastname", String),
    Column("address", String),
    Column("hiring_date", String),
    Column("department", String),
    Column("contract_type", String),
    Column("salary", Integer),
    Column("pto_days", Integer),

    UniqueConstraint("id"),
    schema="hr"
)

employees_activity_table = Table(
    "employees_activity",
    meta,
    Column("employee_id", ForeignKey("employees.id"), primary_key=True),
    Column("strava_user_id", Integer, unique=True),
    Column("commute_type", String, nullable=False),
    Column("commute_distance", Float),
    Column("commute_duration", Float),
    Column("sport_type", String, nullable=True),

    UniqueConstraint("employee_id"),
    schema="hr"
)

