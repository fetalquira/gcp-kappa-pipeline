# infra/iam.tf (Append to bottom)

# Create the dedicated Frontend Service Account
resource "google_service_account" "frontend_sa" {
  account_id   = "bakery-frontend-identity"
  display_name = "Bakery Frontend Identity"
}

# Grant it permission to ONLY publish to Pub/Sub
resource "google_project_iam_member" "frontend_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.frontend_sa.email}"
}

# Create the dedicated Backend Service Account
resource "google_service_account" "backend_sa" {
  account_id   = "bakery-backend-worker"
  display_name = "Bakery Backend Worker"
}

# Grant it permission to write to Firestore
resource "google_project_iam_member" "backend_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Grant it permission to subscribe to Pub/Sub
resource "google_project_iam_member" "backend_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}