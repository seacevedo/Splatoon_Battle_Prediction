terraform {
  required_version = ">= 1.0"
  backend "local" {}  # Can change from "local" to "gcs" (for google) or "s3" (for aws), if you would like to preserve your tf-state online
  required_providers {
    google = {
      source  = "hashicorp/google"
    }
  }
}

provider "google" {
  project = var.GOOGLE_CLOUD_PROJECT_ID
  region = var.GOOGLE_CLOUD_REGION
  credentials = file(var.SERVICE_ACCOUNT_FILE_PATH)
}

# Data Lake Bucket
# Ref: https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket
resource "google_storage_bucket" "google-cloud-bucket" {
  name          = var.GOOGLE_CLOUD_BUCKET_NAME  # Concatenating DL bucket & Project name for unique naming
  location      = var.GOOGLE_CLOUD_REGION

  # Optional, but recommended settings:
  storage_class = var.GOOGLE_CLOUD_BUCKET_STORAGE_CLASS
  uniform_bucket_level_access = true

  versioning {
    enabled     = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 60  // days
    }
  }

  force_destroy = true
}


resource "google_storage_bucket_object" "column_file" {
  name     = "../prod_model/one_hot_columns.pkl"
  source   = "../prod_model/one_hot_columns.pkl"
  bucket   = google_storage_bucket.google-cloud-bucket.id
}

resource "google_storage_bucket_object" "model_file" {
  name     = "../prod_model/current_prod_model.pkl"
  source   = "../prod_model/current_prod_model.pkl"
  bucket   = google_storage_bucket.google-cloud-bucket.id
}

# DWH
# Ref: https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/bigquery_dataset
resource "google_bigquery_dataset" "dataset" {
  dataset_id = var.BQ_DATASET_ID
  project    = var.GOOGLE_CLOUD_PROJECT_ID
  location   = var.GOOGLE_CLOUD_REGION
}

resource "google_compute_instance" "project-vm" {
    name = var.COMPUTE_VM_NAME
    machine_type = var.COMPUTE_VM_MACHINE_TYPE
    zone = var.COMPUTE_VM_REGION

    metadata = {
      ssh-keys = "${var.SSH_USER}:${file(var.SSH_PUBLIC_KEY_PATH)}"
      #startup-script = "git clone https://github.com/seacevedo/Splatoon_Battle_Prediction.git"
      "SERVICE_ACCOUNT_JSON" = "${file(var.SERVICE_ACCOUNT_FILE_PATH)}"
    }

    metadata_startup_script = "git clone https://github.com/seacevedo/Splatoon_Battle_Prediction.git"


    boot_disk {
        initialize_params {
            image = var.COMPUTE_VM_IMG
        }
    }

    service_account {
        email  = var.SERVICE_ACCOUNT_EMAIL
        scopes = ["cloud-platform"]
    }

    network_interface {
        network = "default"
        access_config {

        }
  }


}


resource "google_cloud_run_v2_service" "default_cloud_run" {
  name     = var.CLOUD_RUN_SERVICE_NAME
  location = var.GOOGLE_CLOUD_REGION
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.DOCKER_IMAGE_URL
      ports {
        container_port = 9696
      }
    }
  }
}

data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location    = google_cloud_run_v2_service.default_cloud_run.location
  project     = google_cloud_run_v2_service.default_cloud_run.project
  service     = google_cloud_run_v2_service.default_cloud_run.name
  policy_data = data.google_iam_policy.noauth.policy_data
}
