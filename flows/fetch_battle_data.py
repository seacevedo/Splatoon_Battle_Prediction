import pandas as pd
import glob
from prefect import task
import requests
from prefect_gcp.cloud_storage import GcsBucket
from datetime import date, timedelta
import os
from prefect_gcp.bigquery import bigquery_load_cloud_storage
from prefect_gcp import GcpCredentials
from prefect_gcp.bigquery import bigquery_query


@task(name = 'Load data to bucket')
def load_battle_data_gcs(data_path: str) -> None:
    # Write data to gcs bucket
    gcs_block = GcsBucket.load("splatoon-battle-data")
    gcs_block.upload_from_folder(from_folder=data_path, to_folder=data_path)


def upload_data_bigquery(file_name: str, data_path: str) -> None:
    gcp_credentials_block = GcpCredentials.load("gcp-creds")

    bigquery_load_cloud_storage(
        dataset="splatoon_battle_data",
        table="battle_data",
        uri=f"gs://splatoon-data-bucket/{data_path}/{file_name}",
        gcp_credentials=gcp_credentials_block,
        location='us'
    )


def retrive_data_bq(query: str) -> pd.DataFrame:
    gcp_credentials_block = GcpCredentials.load("gcp-creds")
    df = bigquery_query(query, gcp_credentials_block, to_dataframe=True)
    print(df.tail())
    return df


@task(name="Extract Splatoon Battle Data", log_prints=True)
def extract_battle_data(data_path: str) -> None:
    os.makedirs(data_path, exist_ok=True)
    #date_list = pd.date_range(start=date.today() - timedelta(days = 30 * num_months + 1), end=date.today(), freq='D')
    #for item in date_list:
    yesterday_date = date.today() - timedelta(days = 1)
    file_name = str(yesterday_date.year) + '-' + str(yesterday_date.strftime("%m")) + '-' + str(yesterday_date.strftime("%d")) + '.csv'
    file_url = 'https://dl-stats.stats.ink/splatoon-3/battle-results-csv/' + str(yesterday_date.year) + '/' + str(yesterday_date.strftime("%m")) + '/' + file_name
    print(file_url)
    if not os.path.isfile(data_path + '/' + file_name):
        response = requests.get(file_url)
        with open(data_path + '/' + file_name, 'wb') as file:
            file.write(response.content)


    

@task(name="Transform Splatoon Battle Data", log_prints=True)
def transform_battle_data(data_path: str) -> str:
    all_filenames = [i for i in glob.glob(str(data_path) + '/*.{}'.format('csv'))]
    df = pd.concat([pd.read_csv(f) for f in all_filenames])

    new_column_list = ['-kill-assist', '-kill', '-assist', '-death', '-special', '-inked']
    team_list = ['A', 'B']

    for column in new_column_list:
        for team in team_list:
            column_names = [("{0}" + column).format(team + str(i)) for i in range(1, 5)]
            df[team + column] = df[column_names].sum(axis=1)

    df['kill_diff'] = df['A-kill']-df['B-kill']
    df['assist_diff'] = df['A-assist']-df['B-assist']
    df['death_diff'] = df['A-death']-df['B-death']
    df['special_diff'] = df['A-special']-df['B-special']
    df['inked_diff'] = df['A-inked']-df['B-inked']

    num_columns = ['period', 'kill_diff', 'assist_diff', 'death_diff', 'special_diff', 'inked_diff', 'time']
    cat_columns = ['mode', 'stage', 'lobby', 'win']

    df = df[num_columns + cat_columns]

    file_name = str(date.today()) + '_merged.csv'

    print(df)

    df.to_csv(os.path.join(data_path, file_name))


    return file_name


