resource "google_pubsub_topic" "bakery_orders" {
    name = "incoming-orders"
}