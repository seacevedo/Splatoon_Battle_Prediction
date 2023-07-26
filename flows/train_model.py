import os
import pickle
import shutil
from typing import Tuple
from datetime import date
from functools import partial

import numpy as np
import wandb
import pandas as pd
from prefect import task
from catboost import Pool, CatBoostClassifier
from sklearn.preprocessing import MinMaxScaler, LabelBinarizer
from sklearn.model_selection import train_test_split


@task(name="Prepare data for Training", log_prints=True)
def feature_engineering(
    df: pd.DataFrame, wandb_project: str, wandb_entity: str, artifact_path: str
) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    run = wandb.init(
        project=wandb_project, entity=wandb_entity, job_type="Feature Engineering"
    )

    num_columns = [
        'kill_diff',
        'assist_diff',
        'death_diff',
        'special_diff',
        'inked_diff',
        'time',
    ]
    cat_columns = ['mode', 'stage', 'lobby']

    X = df[num_columns + cat_columns]
    y = df[['win']]

    X_train, X_test, y_train, y_test = train_test_split(X[num_columns + cat_columns], y)
    X_train = pd.get_dummies(X_train, columns=cat_columns, drop_first=True)
    X_test = pd.get_dummies(X_test, columns=cat_columns, drop_first=True)

    scaler = MinMaxScaler()

    scaler.fit(X_train[num_columns])
    X_train[num_columns] = scaler.transform(X_train[num_columns])
    X_test[num_columns] = scaler.transform(X_test[num_columns])

    lb = LabelBinarizer()

    lb.fit(y_train)
    y_train = lb.transform(y_train)
    y_test = lb.transform(y_test)

    artifact_date = str(date.today())

    artifact_data_path = artifact_path + '/scaled_data/'

    os.makedirs(artifact_data_path, exist_ok=True)

    X_train.to_parquet(
        os.path.join(artifact_data_path, artifact_date + "_X_train.parquet")
    )

    with open(
        artifact_data_path + '/' + artifact_date + "_y_train.pkl", "wb"
    ) as train_artifact:
        pickle.dump(y_train, train_artifact)

    X_test.to_parquet(
        os.path.join(artifact_data_path, artifact_date + "_X_test.parquet")
    )

    with open(
        artifact_data_path + '/' + artifact_date + "_y_test.pkl", "wb"
    ) as test_artifact:
        pickle.dump(y_test, test_artifact)

    artifact_name_scaled = artifact_date + '_scaled_data'

    artifact = wandb.Artifact(artifact_name_scaled, type="scaled_data")
    artifact.add_dir(artifact_path)
    run.log_artifact(artifact)
    run.finish()

    return X_train, X_test, y_train, y_test


def train_model(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: np.ndarray,
    y_test: np.ndarray,
    artifact_path: str,
):
    wandb.init()
    config = wandb.config

    wandb_callback = wandb.catboost.WandbCallback()

    train_pool = Pool(
        X_train, y_train, X_train.select_dtypes(['uint8']).columns.to_list()
    )

    test_pool = Pool(X_test, y_test, X_test.select_dtypes(['uint8']).columns.to_list())

    catboost_model = CatBoostClassifier(
        iterations=1000,
        custom_loss=['Accuracy'],
        loss_function='Logloss',
        max_depth=config.max_depth,
        l2_leaf_reg=config.l2_leaf_reg,
        learning_rate=config.learning_rate,
        bagging_temperature=config.bagging_temperature,
        use_best_model=True,
        eval_metric='AUC',
        od_type="Iter",
    )

    catboost_model.fit(train_pool, eval_set=test_pool, callbacks=[wandb_callback])

    artifact_model_path = artifact_path + '/model/'

    os.makedirs(artifact_model_path, exist_ok=True)

    with open(
        artifact_model_path
        + '/'
        + f'catboost_cat_max_depth_{0}_l2_leaf_reg_{1}_ \
            learning_rate_{2}_bagging_temperature_{3}.pkl'.format(
            config.max_depth,
            config.l2_leaf_reg,
            config.learning_rate,
            config.bagging_temperature,
        ),
        'wb',
    ) as model_file:
        pickle.dump(catboost_model, model_file)

    with open(artifact_model_path + '/one_hot_columns.pkl', 'wb') as one_hot_file:
        pickle.dump(X_train.columns.tolist(), one_hot_file)

    artifact_date = str(date.today())

    artifact = wandb.Artifact(artifact_date + '_trained_model', type="catboost_model")
    artifact.add_dir(artifact_path)
    wandb.log_artifact(artifact)


SWEEP_CONFIG = {
    "method": "bayes",
    "metric": {"name": "Accuracy", "goal": "minimize"},
    "parameters": {
        "max_depth": {
            "distribution": "int_uniform",
            "min": 1,
            "max": 10,
        },
        "l2_leaf_reg": {
            "distribution": "int_uniform",
            "min": 1,
            "max": 100,
        },
        "learning_rate": {
            "distribution": "uniform",
            "min": 0.01,
            "max": 0.1,
        },
        "bagging_temperature": {
            "distribution": "uniform",
            "min": 0.01,
            "max": 0.7,
        },
    },
}


@task(name="Optimize Model Parameters", log_prints=True)
def optimize(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: np.ndarray,
    y_test: np.ndarray,
    wandb_project: str,
    wandb_entity: str,
    artifact_path: str,
    count: int,
):
    sweep_id = wandb.sweep(SWEEP_CONFIG, project=wandb_project, entity=wandb_entity)
    wandb.agent(
        sweep_id,
        partial(train_model, X_train, X_test, y_train, y_test, artifact_path),
        count=count,
    )

    api = wandb.Api()
    sweep = api.sweep(f"{wandb_entity}/{wandb_project}/sweeps/{sweep_id}")

    prod_model_path = '../prod_model'

    os.makedirs(prod_model_path, exist_ok=True)
    artifact_model_path = artifact_path + '/model/'

    # Get best run parameters
    best_run = sweep.best_run()
    best_parameters = best_run.config
    prod_model_file_name = f'catboost_cat_max_depth_{0}_l2_leaf_reg_{1}_ \
    learning_rate_{2}_bagging_temperature_{3}.pkl'.format(
        best_parameters['max_depth'],
        best_parameters['l2_leaf_reg'],
        best_parameters['learning_rate'],
        best_parameters['bagging_temperature'],
    )
    shutil.copyfile(
        artifact_model_path + prod_model_file_name,
        prod_model_path + '/current_prod_model.pkl',
    )
    shutil.copyfile(
        artifact_model_path + '/one_hot_columns.pkl',
        prod_model_path + '/one_hot_columns.pkl',
    )
