FROM apache/airflow:3.1.8

RUN PWD
RUN mkdir -p opt/app/

COPY hr/* /opt/app/hr/
COPY slack/* /opt/app/slack/
COPY dashboards/* /opt/app/dashboards/
COPY requirements.txt /

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/opt/airflow:/opt/airflow/dags:/opt/app/:$PYTHONPATH

WORKDIR /opt/app