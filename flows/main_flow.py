import sys

from prefect import flow
from train_model import optimize, feature_engineering
from monitor_model import batch_monitoring_fill
from fetch_battle_data import (
    retrieve_data_bq,
    extract_battle_data,
    load_battle_data_gcs,
    upload_data_bigquery,
    transform_battle_data,
)


@flow
def run_pipeline(
    data_path: str,
    wandb_project: str,
    wandb_entity: str,
    artifact_path: str,
    num_months: int,
    gcp_project_id: str,
    bigquery_dataset: str,
    bigquery_table: str,
):
    extract_battle_data(data_path, num_months)
    file_name = transform_battle_data(data_path, num_months)
    load_battle_data_gcs(data_path)
    upload_data_bigquery(file_name, data_path)
    current_data_query = f'''SELECT * FROM `{0}.{1}.{2}`
                            WHERE DATE(period) BETWEEN
                            DATE_SUB(CURRENT_DATE(), INTERVAL {3} MONTH) AND CURRENT_DATE()
                            ORDER BY period;'''.format(
        gcp_project_id, bigquery_dataset, bigquery_table, num_months
    )
    current_data_df = retrieve_data_bq(current_data_query)
    print(current_data_df.head())
    X_train, X_test, y_train, y_test = feature_engineering(
        current_data_df, wandb_project, wandb_entity, artifact_path
    )
    optimize(
        X_train, X_test, y_train, y_test, wandb_project, wandb_entity, artifact_path, 1
    )
    load_battle_data_gcs('../prod_model')
    reference_data_query = f'''SELECT * FROM `{0}.{1}.{2}`
                              WHERE DATE(period) BETWEEN
                              DATE_SUB(DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY),
                              INTERVAL {3} MONTH) AND DATE_SUB(CURRENT_DATE(),
                              INTERVAL 1 DAY);'''.format(
        gcp_project_id, bigquery_dataset, bigquery_table, num_months
    )
    reference_data_df = retrieve_data_bq(reference_data_query)
    batch_monitoring_fill(current_data_df, reference_data_df)


if __name__ == '__main__':
    data_path = sys.argv[1]
    wandb_project = sys.argv[2]
    wandb_entity = sys.argv[3]
    artifact_path = sys.argv[4]
    num_months = sys.argv[5]
    gcp_project_id = sys.argv[6]
    bigquery_dataset = sys.argv[7]
    bigquery_table = sys.argv[8]
    run_pipeline(
        data_path,
        wandb_project,
        wandb_entity,
        artifact_path,
        num_months,
        gcp_project_id,
        bigquery_dataset,
        bigquery_table,
    )
