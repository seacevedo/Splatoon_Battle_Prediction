'''CatBoostClassifer import not used directly in code,
but needed to import model from pickle file and make predictions'''
# pylint: disable=unused-import


import os
import pickle

import numpy as np
import pandas as pd
from flask import Flask, request, send_file, render_template
from catboost import CatBoostClassifier
from google.cloud import storage
from sklearn.preprocessing import MinMaxScaler

app = Flask('winner-prediction')
UPLOAD_FOLDER = "/home/seacevedo/app/static/files"


def prepare_features(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    new_column_list = [
        '-kill-assist',
        '-kill',
        '-assist',
        '-death',
        '-special',
        '-inked',
    ]
    team_list = ['A', 'B']

    for column in new_column_list:
        for team in team_list:
            column_names = [("{0}" + column).format(team + str(i)) for i in range(1, 5)]
            df[team + column] = df[column_names].sum(axis=1)

    df['kill_diff'] = df['A-kill'] - df['B-kill']
    df['assist_diff'] = df['A-assist'] - df['B-assist']
    df['death_diff'] = df['A-death'] - df['B-death']
    df['special_diff'] = df['A-special'] - df['B-special']
    df['inked_diff'] = df['A-inked'] - df['B-inked']

    num_columns = [
        'time',
        'kill_diff',
        'assist_diff',
        'death_diff',
        'special_diff',
        'inked_diff',
    ]
    cat_columns = ['mode', 'stage', 'lobby']

    df = df[num_columns + cat_columns]

    return df


def predict(df: pd.DataFrame):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket('splatoon-data-bucket')
    blob_cols = bucket.blob('../prod_model/one_hot_columns.pkl')
    blob_model = bucket.blob('../prod_model/current_prod_model.pkl')

    pickle_cols = blob_cols.download_as_string()
    columns = pickle.loads(pickle_cols)

    pickle_model = blob_model.download_as_string()
    model = pickle.loads(pickle_model)

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

    X = pd.get_dummies(X, columns=cat_columns, drop_first=True)

    scaler = MinMaxScaler()
    scaler.fit(X[num_columns])
    X[num_columns] = scaler.transform(X[num_columns])

    X = X.reindex(columns=columns).fillna(0)

    one_hot_encoded_cols = list(set(columns).difference(num_columns))

    X[one_hot_encoded_cols] = X[one_hot_encoded_cols].astype(int)

    predictions = model.predict(X)

    return predictions


def add_predictions(path: str, predictions: np.ndarray) -> pd.DataFrame:
    df = pd.read_csv(path)
    predictions = predictions.astype(str)
    predictions[predictions == '0'] = 'alpha'
    predictions[predictions == '1'] = 'bravo'
    df['prediction'] = predictions
    pred_location = os.path.join(UPLOAD_FOLDER, 'predictions.csv')
    df.to_csv(pred_location)


@app.route("/download_predict", methods=['GET'])
def download_predict():
    csv_location = os.path.join(UPLOAD_FOLDER, 'predictions.csv')
    return send_file(csv_location, as_attachment=True)


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        csv_file = request.files["file_csv"]
        if csv_file:
            csv_location = os.path.join(UPLOAD_FOLDER, csv_file.filename)
            csv_file.save(csv_location)
            df = prepare_features(csv_location)
            pred = predict(df)
            add_predictions(csv_location, pred)
            return render_template("index.html", csv_loc=csv_file.filename)
    return render_template("index.html", csv_loc=None)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=9696)
