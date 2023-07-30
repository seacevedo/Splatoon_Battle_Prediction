# prefect package imports are actually seperate, looks like they are in same module
# pylint: disable=ungrouped-imports

import pickle
from typing import Any
from datetime import date

import pandas as pd
import psycopg
from prefect import task
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metrics import (
    ColumnDriftMetric,
    DatasetDriftMetric,
    DatasetMissingValuesMetric,
)
from prefect.blocks.system import Secret
from sklearn.preprocessing import MinMaxScaler


def prep_db(db_username_secret: Any, db_password_secret: Any):
    create_table_statement = """
        create table if not exists monitoring_metrics(
            timestamp timestamp,
            prediction_drift float,
            num_drifted_columns integer,
            share_missing_values float
        );"""

    with psycopg.connect(
        (
            f"host=localhost port=5432 user={db_username_secret.get()} password="
            f"{db_password_secret.get()}"
        ),
        autocommit=True,
    ) as conn:
        res = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname='evidently_metrics';"
        )
        if len(res.fetchall()) == 0:
            conn.execute("create database evidently_metrics;")
        with psycopg.connect(
            (
                f"host=localhost port=5432 dbname=evidently_metrics user="
                f"{db_username_secret.get()} password={db_password_secret.get()}"
            )
        ) as conn:
            conn.execute(create_table_statement)


def calculate_metrics_postgresql(
    curr: Any,
    current_data: pd.DataFrame,
    reference_data: pd.DataFrame,
) -> float:
    with open('../prod_model/current_prod_model.pkl', 'rb') as f_in:
        model = pickle.load(f_in)

    num_columns = [
        'kill_diff',
        'assist_diff',
        'death_diff',
        'special_diff',
        'inked_diff',
        'time',
    ]
    cat_columns = ['mode', 'stage', 'lobby']

    current_data = current_data[num_columns + cat_columns]
    reference_data = reference_data[num_columns + cat_columns]

    current_data = pd.get_dummies(current_data, columns=cat_columns, drop_first=True)
    reference_data = pd.get_dummies(
        reference_data, columns=cat_columns, drop_first=True
    )

    scaler = MinMaxScaler()

    scaler.fit(current_data[num_columns])
    current_data[num_columns] = scaler.transform(current_data[num_columns])
    scaler.fit(reference_data[num_columns])
    reference_data[num_columns] = scaler.transform(reference_data[num_columns])

    current_data['prediction'] = model.predict(current_data)
    reference_data['prediction'] = model.predict(reference_data)

    print('Here 3')

    print(current_data.head())
    print(reference_data.head())

    cat_columns = list(set(current_data.columns) - set(num_columns))
    print(cat_columns)

    column_mapping = ColumnMapping(
        prediction='prediction',
        numerical_features=num_columns,
        categorical_features=cat_columns,
        target=None,
    )

    report = Report(
        metrics=[
            ColumnDriftMetric(column_name='prediction'),
            DatasetDriftMetric(),
            DatasetMissingValuesMetric(),
        ]
    )

    report.run(
        reference_data=reference_data,
        current_data=current_data,
        column_mapping=column_mapping,
    )

    result = report.as_dict()

    prediction_drift = result['metrics'][0]['result']['drift_score']
    num_drifted_columns = result['metrics'][1]['result']['number_of_drifted_columns']
    share_missing_values = result['metrics'][2]['result']['current'][
        'share_of_missing_values'
    ]

    curr.execute(
        (
            "insert into monitoring_metrics(timestamp,prediction_drift,num_drifted_columns,"
            "share_missing_values) values (%s, %s, %s, %s);"
        ),
        (date.today(), prediction_drift, num_drifted_columns, share_missing_values),
    )

    return prediction_drift


@task(name="Prepare database and calculate metrics to save as record", log_prints=True)
def batch_monitoring_fill(
    current_data: pd.DataFrame, reference_data: pd.DataFrame
) -> float:
    db_username_secret = Secret.load("db-username")
    db_password_secret = Secret.load("db-password")
    prep_db(db_username_secret, db_password_secret)
    with psycopg.connect(
        (
            f"host=localhost port=5432 dbname=evidently_metrics user="
            f"{db_username_secret.get()} password={db_password_secret.get()}"
        ),
        autocommit=True,
    ) as conn:
        with conn.cursor() as curr:
            drift_value = calculate_metrics_postgresql(
                curr, current_data, reference_data
            )
        conn.close()
    return drift_value
