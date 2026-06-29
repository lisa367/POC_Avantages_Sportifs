from sqlalchemy import MetaData, Table, Column, Integer, Float, Boolean, DateTime, UniqueConstraint

meta = MetaData()


primes_sportives_table = Table(
    "primes_sportives",
    meta,
    Column("employee_id", Integer, primary_key=True),
    Column("prime_sportive_eligibilite", Boolean),
    Column("prime_sportive_montant", Float),
    Column("seances_sport", Integer),
    Column("row_updated_at", DateTime),

    UniqueConstraint("employee_id"),
    schema="dashboards"
)