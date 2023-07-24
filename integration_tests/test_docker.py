import requests
import pandas as pd

files = {'file_csv': open('test.csv', 'rb')}
upload_url = 'http://localhost:9696/'

r = requests.post(upload_url, files=files)

download_url = 'http://localhost:9696/download_predict'
df = pd.read_csv(download_url)

predicted_result = df['prediction'].to_list()
expected_results = ['bravo', 'bravo', 'alpha', 'bravo', 'alpha', 'alpha', 'bravo', 'bravo', 'alpha']

assert predicted_result == expected_results