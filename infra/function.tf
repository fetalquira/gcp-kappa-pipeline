# 1. Create the bucket to store the code zip (The "Attic")
resource "google_storage_bucket" "function_bucket" {
  name                        = "${var.project_id}-function-source"
  location                    = "ASIA-SOUTHEAST1"
  uniform_bucket_level_access = true
}

# 2. Tell Terraform to zip your backend folder
# This tells Terraform: "Grab the backend folder, AND grab this specific file"
data "archive_file" "function_zip" {
  type        = "zip"
  output_path = "${path.module}/files/function.zip"

  # This tells Terraform to take the whole backend folder content
  source {
    content  = file("${path.module}/../backend/main.py")
    filename = "main.py"
  }

  source {
    content  = file("${path.module}/../backend/requirements.txt")
    filename = "requirements.txt"
  }

  # MANUALLY ADD THE SHARED SCHEMA (The "Successor" Fix)
  # This places the shared file directly into the root of the zip
  source {
    content  = file("${path.module}/../shared/src/shared/schemas.py")
    filename = "schemas.py"
  }
}

# 3. Upload that zip to the bucket
resource "google_storage_bucket_object" "zip_upload" {
  name   = "source.${data.archive_file.function_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.function_zip.output_path
}

# 4. Deploy the Cloud Function
resource "google_cloudfunctions_function" "order_processor" {
  name        = "bakery-order-processor"
  description = "Successor Order Processor"
  runtime     = "python312"

  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.zip_upload.name
  entry_point           = "process_order" # Must match the def in main.py

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.bakery_orders.id
  }

  environment_variables = {
    PROJECT_ID = var.project_id
    TARGET_DB_NAME = var.db_name
  }
}