output "frontend_url" {
  description = "The public URL of the bakery frontend"
  # This pulls the URI attribute from the Cloud Run service resource
  value       = google_cloud_run_v2_service.frontend.uri
}