<p align="center">
  <img src="https://i.imgur.com/zLXjmgw.png" />
</p>

## Purpose

Splatoon 3 is the latest entry in the Splatoon series by Nintendo. It has garnered a massive following, even having a reach into competitive gaming. The purpose of this project is to provide a Machine Learning solution that can predict victors from past game data. Such a tool would be useful in tournaments to predict winners of games being played in real time.


## Technology Stack

* [Google Cloud](https://cloud.google.com/) to upload data to a google cloud bucket and use BigQuery as our data warehouse. We will also set up a VM environment to host our prefect deployment.
* [Terraform](https://www.terraform.io/) for version control of our infrastructure.
* [Prefect](https://www.prefect.io/) will be used to orchestrate and monitor our pipeline. 
* [Pandas](https://pandas.pydata.org/) to import and transform our dataset.
* [splat.ink](https://stat.ink/index?_lang_=en-US) to access splatoon 3 battle data. You can learn more about the columns of data set [here](https://github.com/fetus-hina/stat.ink/wiki/Spl3-%EF%BC%8D-CSV-Schema-%EF%BC%8D-Battle).
* [Weights and Biases](https://wandb.ai/site) to track model performance and keep track of models and datasets used.
* [Evidently](https://www.evidentlyai.com/) to monitor dataset drift.
* [Postgres](https://www.postgresql.org/) to save dataset drift metrics
* [Grafana](https://grafana.com/) to monitor dataset drift
* [Docker](https://www.docker.com/) to containerize deployed model and monitoring architecture
* [Docker Compose](https://docs.docker.com/compose/) for managing multiple docker containers used in this project
* [Pre-Commit Hooks](https://pre-commit.com/) to identify simple issues in code before review
* [Github Actions](https://github.com/features/actions) to prevent issues and making sure tests work before merging with main branch. Once merged with main, the deployment process is initiated.
## Pipeline Architecture
![alt_text](https://github.com/seacevedo/Splatoon_Battle_Prediction/blob/main/images/mlops_architecture.png)

* Terraform is used to setup the environment to run our pipeline. When run, the script creates our BigQuery dataset, bucket, deploys a Docker containerized production model to Google Cloud Run, and our VM to run our Prefect deployment.
* A Prefect agent is run on our VM compute environment and runs any pending deployments. The pipeline is meant to be run every N months. Initially, the pipeline extracts Splatoon 3 battle data from stat.ink, adds the raw data to a GCS bucket, cleans the data and performs feature engineering and extraction, and then moves the resulting the data to a BigQuery dataset. The data from bigquery is then used to train different models until an optimal one is selected, which will be registered in Weights and Biases and a production folder in the bucket. A reference dataset will be queried from BigQuery to be used as a comparison to the training dataset to see if data drift exists. This is calculated by Evidently, which triggers a notification if this occurs.
* Evidently will record any drift metrics to a postgres database. This database will be queried by a grafana dashboard to monitor drift. This infrastructure is orchestrated by Docker Compose.


## Deployment Preview
Access the deployed model [here](https://app-run-service-gq2tu4do3a-uc.a.run.app/). You can use it by uploading a CSV file containing raw Splatoon 3 battle data from stat.ink. After uploading, a link to a file with your results should pop up. Click the link to download the resuling file. Results should be under the `prediction` column.

![alt_text](https://github.com/seacevedo/Solana-Pipeline/blob/main/dashboard_preview.png)

## Replication Steps

### Create a Reddit Account

1. You must create a reddit account in order to be able to scrape subreddit data. 
2. Once you have an account go [here](https://www.reddit.com/prefs/apps). Click on the `create another app...` button at the bottom of the page. Fill in the required fields and select `web app`. Click on `create app`
3. Under the `web_app` text under your newly created app information you should have an id for your application. Record this and the secret key. You will need to parameterize your flow with these tokens in order to use the PRAW apiSetup Google Cloud 

### Setup Google Cloud 

1. Create a google cloud account
2. Setup a new google cloud [project](https://cloud.google.com/).
3. Create a new service account. Give the service account the `Compute Admin`, `Service Account User`, `Storage Admin`, `Storage Object Admin`, and `BigQuery Admin` Roles.
4. After the service account has been created, click on `Manage Keys` under the `Actions` Menu. Click on the `Add Key` dropdown and click on `Create new key`. A prompt should pop up asking to download it as a json or P12 file. Choose the json format and click `Create`. Save your key file.
5. Install the the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install-sdk). Assuming you have an Ubuntu linux distro or similar as your environment, follow the directions for `Debian/Ubuntu`. Make sure you log in by running `gcloud init`. Choose the cloud project you created to use.
6. Set the environment variable to point to your downloaded service account keys json file:

`export GOOGLE_APPLICATION_CREDENTIALS=<path/to/your/service-account-authkeys>.json`

7. Refresh token/session, and verify authentication
`gcloud auth application-default login`

8. Make sure these APIs are enabled for your project:

https://console.cloud.google.com/apis/library/iam.googleapis.com
https://console.cloud.google.com/apis/library/iamcredentials.googleapis.com
https://console.cloud.google.com/apis/library/compute.googleapis.com

### Setup VM Environment

1. Clone the repo and `cd` into the `Solana-Pipeline` folder
2. Install [Terraform](https://www.terraform.io/)
3. Make sure you have an SSH key generated to log into the VM.
4. `cd` to the `terraform` directory and enter the commands `terraform init`, `terraform plan`, and `terraform apply`. You can remove the corresponding infrastructure by using `terraform destroy`. For the plan and destroy commands you will be prompted to input the following variables:

| Variable       | Description  |
| ------------- |:-------------:|
| GOOGLE_CLOUD_PROJECT_ID      | ID of the google cloud project | 
| SERVICE_ACCOUNT_EMAIL     | Email of the service account you used to generate the key file  | 
| SSH_USER | Username you used for the SSH Key   |  
| SSH_PUBLIC_KEY_PATH | Path to the public SSH key      |
| SETUP_SCRIPT_PATH | Path of the setup.sh script within the Solana-Pipeline directory     | 
| SERVICE_ACCOUNT_FILE_PATH | Keyfile of the service account   | 
| GOOGLE_CLOUD_BUCKET_NAME | Name of your GCS bucket   | 

5. Log in your newly created VM environment using the following command `ssh -i /path/to/private/ssh/key username@vm_external_ip_address`. As an alternative, follow this [video](https://www.youtube.com/watch?v=ae-CV2KfoN0&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb) to help setup SSH in a VS code environment, which allows for port forwarding from your cloud VM to your local machine. Type the command `cd /Solana-Pipeline` to `cd` into the `/Solana-Pipeline` directory. Login as super user with the command `sudo su` in order to edit files.
6. Activate the newly created python virtual environment using the command: `source solana-pipeline-env/bin/activate` (You may have to wait a few minutes in order for the vm instance to finish running the setup.sh script and installing all necessary dependancies).
7. Make sure you update the profiles.yml and schema.yml files in your dbt directory. Change the appropriate fields with the correct google cloud project id, dataset name, location, and keyfile path. 
8. You should now have prefect installed. Run the prefect server locally using the `prefect orion start` command to monitor flows. This is needed to access the Orion UI. In another terminal, `cd` into the `flows` directory and run the command `prefect deployment build main_flow.py:run_pipeline -n "solana-pipeline-deployment" --cron "0 0 * * *" -a` to build the prefect deployment that runs at 12:00 AM every day. Make sure you setup the following prefect blocks before running:

| Block Name       | Description  |
| ------------- |:-------------:|
| crypto-gcp-creds      | Block pertaining to your Google cloud credentials. You need the JSON keyfile you downloaded earlier to set it up | 
| crypto-reddit   | Block pertaining to the bucket you wish to load the data into | 

  
9. You can then run the deployment using the command `prefect deployment run run-pipeline/solana-pipeline-deployment --params '{"client_id":<client_id>, "client_secret":<client_secret>, "reddit_username":<reddit_username>, "bucket_name":"solana_reddit", "dbt_dir":"/Solana-Pipeline/solana_subreddit_dbt/", "subreddit":"solana", "subreddit_cap":100, "bq_dataset_location":"us-central1", "num_days":15}'` as an example. The deployment should be scheduled.
10. Your newly scheduled deployment can be run when initiating a prefect agent. Run the command `prefect agent start -q "default"` to run your deployment.

## Next Steps
* Add CI/CD tooling to automate the workflow and make it more production ready
* Take advantage of systemd to run the agent when the VM starts up
* Add Piperider to allow for data profiling and monitoring
* Add docker containers to aid with reproducibility of the presented pipeline.
