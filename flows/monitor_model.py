from prefect import task
import psycopg
from evidently.report import Report
from evidently import ColumnMapping
from evidently.metrics import ColumnDriftMetric, DatasetDriftMetric, DatasetMissingValuesMetric
import pandas as pd
from datetime import date
import pickle
from prefect.blocks.system import Secret
from typing import Tuple, Any


def prep_db(db_username_secret: Any, db_password_secret: Any) -> None:
	create_table_statement ="""
        create table if not exists monitoring_metrics(
            timestamp timestamp,
            prediction_drift float,
            num_drifted_columns integer,
            share_missing_values float
        )"""
	
	
	with psycopg.connect("host=localhost port=5432 user={0} password={1}".format(db_username_secret.get(), db_password_secret.get()), autocommit=True) as conn:
		res = conn.execute("SELECT 1 FROM pg_database WHERE datname='evidently_metrics'")
		if len(res.fetchall()) == 0:
			conn.execute("create database evidently_metrics;")
		with psycopg.connect("host=localhost port=5432 dbname=evidently_metrics user={0} password={1}".format(db_username_secret.get(), db_password_secret.get())) as conn:
			conn.execute(create_table_statement)

def calculate_metrics_postgresql(curr: Any, artifact_path: str, current_data: pd.DataFrame, reference_data: pd.DataFrame) -> None:

    with open('../prod_model/current_prod_model.pkl', 'rb') as f_in:
         model = pickle.load(f_in)
	 
    num_columns = ['kill_diff', 'assist_diff', 'death_diff', 'special_diff', 'inked_diff', 'time']

    
    #current_data = pd.read_parquet('artifacts/' + str(date.today()) + "_X_train.parquet")
    cat_columns = list(set(current_data.columns) - set(num_columns))
    current_data['prediction'] = model.predict(current_data)
    #reference_data = pd.read_parquet('artifacts/' + str(date.today() - timedelta(1)) + "_X_train.parquet")
    reference_data['prediction'] = model.predict(reference_data)

    
    column_mapping = ColumnMapping(
        prediction='prediction',
        numerical_features=num_columns,
        categorical_features=cat_columns,
        target=None
    )
	
    report = Report(metrics=[
	    ColumnDriftMetric(column_name='prediction'),
        DatasetDriftMetric(),
        DatasetMissingValuesMetric()
    ])
    
    

    report.run(reference_data = reference_data, current_data = current_data, column_mapping=column_mapping)

    result = report.as_dict()

    prediction_drift = result['metrics'][0]['result']['drift_score']
    num_drifted_columns = result['metrics'][1]['result']['number_of_drifted_columns']
    share_missing_values = result['metrics'][2]['result']['current']['share_of_missing_values']


    curr.execute(
         "insert into monitoring_metrics(timestamp, prediction_drift, num_drifted_columns, share_missing_values) values (%s, %s, %s, %s)",
         (date.today(), prediction_drift, num_drifted_columns, share_missing_values)
    )

    return None

@task(name="Prepare database and calculate metrics to save as record", log_prints=True)
def batch_monitoring_fill(artifact_path: str, current_data: pd.DataFrame, reference_data: pd.DataFrame):
	db_username_secret = Secret.load("db-username")
	db_password_secret = Secret.load("db-password")
	prep_db(db_username_secret, db_password_secret)
	with psycopg.connect("host=localhost port=5432 dbname=evidently_metrics user={0} password={1}".format(db_username_secret, db_password_secret), autocommit=True) as conn:
		with conn.cursor() as curr:
			calculate_metrics_postgresql(curr, artifact_path, current_data, reference_data)