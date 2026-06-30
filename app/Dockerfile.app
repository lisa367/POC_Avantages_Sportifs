FROM apache/airflow:3.2.1
USER airflow
# FROM python:3.12-slim

# RUN pwd
# RUN mkdir -p /opt/app/

COPY hr /opt/app/hr/
COPY slack /opt/app/slack/
COPY dashboards /opt/app/dashboards/
COPY requirements.txt .
# COPY requirements.txt /requirements.txt

# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

# RUN pip list >> echo

# ENV PYTHONPATH=/opt/airflow:/opt/airflow/dags:/opt/app/:$PYTHONPATH

WORKDIR /opt/app