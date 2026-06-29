import os
from datetime import datetime as dt
import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
# from airflow.providers.standard.operators.python import PythonOperator


RUN_TIME_SCHEDULE = "0 10 15 * *"

# ENV_VARS = {
#     "EXECUTION_DATE": "{{ yesterday_ds }}",  # on récupère les données de la veille
#     "POSTGRES_USER" : os.environ.get("POSTGRES_USER"),
#     "POSTGRES_PASSWORD" : os.environ.get("POSTGRES_PASSWORD"),
# }

DEFAULT_ARGS = {
    "owner": "airflow",
    "start_date": dt(2025, 5, 1, tzinfo=pendulum.timezone("Europe/Paris")),
    "retries": 0,
    "location": "EU"
}

with DAG(
    dag_id="sport_data_solutions_pipeline",
    default_args=DEFAULT_ARGS,
    tags=["OPC", "P12", "Strava, Metabase"],
    schedule=RUN_TIME_SCHEDULE,
    catchup=False, # backfill=true ?
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end", trigger_rule="none_failed")

    hr_etl = BashOperator(
        task_id="hr_etl",
        bash_command=f"python3 /opt/app/hr/etl.py",
        trigger_rule="none_failed"
    )

    strava_api_db = BashOperator(
        task_id="strava_api_db",
        bash_command=f"python3 /opt/app/strava/models.py",
        trigger_rule="none_failed"
    )

    strava_api_simulator = BashOperator(
        task_id="strava_api_simulator",
        bash_command="uvicorn api:api --reload",
        trigger_rule="none_failed"
    )

    slack_etl = BashOperator(
        task_id="slack_etl",
        bash_command=f"python3 /opt/app/slack/etl.py",
        trigger_rule="none_failed",
    )

    dashboards = BashOperator(
        task_id="dashboards",
        bash_command=f"python3 /opt/app/dashboards/etl.py",
        trigger_rule="none_failed"
    )


(
    start 
    >> hr_etl 
    >> strava_api_db
    >> strava_api_simulator 
    >> slack_etl 
    >> dashboards
    >> end
)

