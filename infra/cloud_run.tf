# infra/cloud_run.tf

# 1. The Artifact Registry (The Garage)
resource "google_artifact_registry_repository" "bakery_repo" {
  location      = "asia-southeast1"
  repository_id = "bakery-pipeline-repo"
  description   = "Docker repository for the Bakery frontend"
  format        = "DOCKER"
}

# 2. The Cloud Run Service (The Fortress)
resource "google_cloud_run_v2_service" "frontend" {
  name     = "bakery-frontend"
  location = "asia-southeast1"
  
  template {
    # Identity Isolation: Using your pre-existing service account
    service_account = google_service_account.frontend_sa.email

    timeout = "60s"
    max_instance_request_concurrency = 50

    # Cost & DDoS Protection
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = "asia-southeast1-docker.pkg.dev/${var.project_id}/bakery-pipeline-repo/bakery-frontend:latest"
      
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
      
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
    }
  }
}

# 3. Public Access (The Gateway)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}