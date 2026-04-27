# This creates the main Firestore database instance
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = var.db_name
  location_id = "asia-southeast1"
  type        = "FIRESTORE_NATIVE"
  delete_protection_state="DELETE_PROTECTION_ENABLED"
}