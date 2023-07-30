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

![alt_text](https://github.com/seacevedo/Splatoon_Battle_Prediction/blob/main/images/prod_model.png)

## Replication Steps


### Setup Google Cloud 

1. Create a google cloud account
2. Setup a new google cloud [project](https://cloud.google.com/).
3. Create a new service account. Give the service account the `Compute Admin`, `Service Account User`, `Storage Admin`, `Storage Object Admin`, `Cloud Run Admin`, and `BigQuery Admin` Roles.
4. After the service account has been created, click on `Manage Keys` under the `Actions` Menu. Click on the `Add Key` dropdown and click on `Create new key`. A prompt should pop up asking to download it as a json or P12 file. Choose the json format and click `Create`. Save your key file.
5. Install the the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install-sdk). Assuming you have an Ubuntu linux distro or similar as your environment, follow the directions for `Debian/Ubuntu`. Make sure you log in by running `gcloud init`. Choose the cloud project you created to use.
6. Set the environment variable to point to your downloaded service account keys json file:

`export GOOGLE_APPLICATION_CREDENTIALS=<path/to/your/service-account-authkeys>.json`

7. Refresh token/session, and verify authentication
`gcloud auth application-default login`

8. Make sure these APIs are enabled for your project:

* https://console.cloud.google.com/apis/library/iam.googleapis.com
* https://console.cloud.google.com/apis/library/iamcredentials.googleapis.com
* https://console.cloud.google.com/apis/library/compute.googleapis.com
* https://console.cloud.google.com/apis/library/run.googleapis.com

### Setup VM Environment

1. Clone the repo and `cd` into the `Splatoon_Battle_Prediction` folder
2. Make any necessary changes and push to new repo, using `git add .`, `git commit -m "my commit message"`, and `git push`. Bfore you do this make sure you have a `main` and `dev` branch. Push changes to dev branch, using the command `git checkout -b dev`.
3. Pre-commit hooks should be running to make changes to files and format code approrpiately. You may need to disable either black or isort hooks as they tend to conflict with one another and prevent successful pushing.
4. After the code has been pushed to the `dev` branch, create a pull request and wait until the `CI Test` Github action step completes successfully. You can then merge with with the `main` branch, which should trigger a deplyment using terraform. You may need to adjust the following variables in the `infrastructure/vars/vars.tfvars` file appropriately:

| Variable       | Description  |
| ------------- |:-------------:|
| GOOGLE_CLOUD_PROJECT_ID      | ID of the google cloud project | 
| SERVICE_ACCOUNT_EMAIL     | Email of the service account you used to generate the key file  | 
| CLOUD_RUN_SERVICE_NAME | Name of your Google Cloud Run Service  | 
| DOCKER_IMAGE_URL | URL of your deployed containerized model | 
| COMPUTE_VM_NAME | Name of your VM Environment  | 

5. You can use the default docker container URL for the deployment of the model or you can construct your own and push it to Docker hub. You can use the Dockerfile in the `deployment` directory for this. Make sure you change the URL in `infrastructure/vars/vars.tfvars` if this is the case.
6. Make sure you add the following repository secret variables as well in order to succesfully pass the `CD Deploy` Github action:

| Variable       | Description  |
| ------------- |:-------------:|
| GOOGLE_APPLICATION_CREDENTIALS      | JSON file containing Google cloud credentials | 
| SSH_PUBLIC_KEY     | SSH Public Key that will be used to access VM environment | 

   
7. Log in your newly created VM environment using the following command `ssh -i /path/to/private/ssh/key username@vm_external_ip_address`. As an alternative, follow this [video](https://www.youtube.com/watch?v=ae-CV2KfoN0&list=PL3MmuxUbc_hJed7dXYoJw8DoCuVHhGEQb) to help setup SSH in a VS code environment, which allows for port forwarding from your cloud VM to your local machine. Type the command `cd /Solana-Pipeline` to `cd` into the `/Solana-Pipeline` directory. Login as super user with the command `sudo su` in order to edit files.
8. Install `make` using the command `sudo apt install make`
9. Create and activate the python pipenv environment using the command: `make setup_pipenv`. You can then run the code quality checks, unit tests, and integration tests using `make integration_testing`.
10. You should now install Docker. Use the following commands, in order:
    *  sudo apt-get install ca-certificates curl gnupg
    *  sudo install -m 0755 -d /etc/apt/keyrings
    *  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    *  sudo chmod a+r /etc/apt/keyrings/docker.gpg
    *  echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    *  sudo apt-get update -y
    *  sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
    *  sudo apt install docker-compose -y
11. Move into the `monitoring` directory using the `cd monitoring` command. Then run the docker containers using the command 
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
