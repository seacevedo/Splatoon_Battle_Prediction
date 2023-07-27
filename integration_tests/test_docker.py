import pandas as pd
import requests

with open('test.csv', 'rb') as file:
    files = {'file_csv': file}
    upload_url = 'http://localhost:9696/'
    r = requests.post(upload_url, files=files, timeout=100)

download_url = 'http://localhost:9696/download_predict'
df = pd.read_csv(download_url)

predicted_result = df['prediction'].to_list()
expected_results = [
    'bravo',
    'bravo',
    'alpha',
    'bravo',
    'alpha',
    'alpha',
    'bravo',
    'bravo',
    'alpha',
]

assert predicted_result == expected_results
