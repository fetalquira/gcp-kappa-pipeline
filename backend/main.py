import base64
import json
import os
from google.cloud import firestore
from schemas import OrderModel # This works because of our Terraform zip magic


# This "Global" initialization reuses the connection across multiple function calls.
db = firestore.Client()

def process_order(event, context):
    """
    Triggered by a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    # 1. Decode the Pub/Sub message
    # Pub/Sub messages arrive as base64 encoded strings
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    data_json = json.loads(pubsub_message)

    try:
        # 2. Validate using your Pydantic Schema
        # This is the "Data Integrity" gate
        order = OrderModel(**data_json)
        
        # 3. Write to Firestore
        # We use the order_id as the Document ID to prevent duplicates
        doc_ref = db.collection("orders").document(order.order_id)
        doc_ref.set(order.model_dump())

        print(f"Successfully processed Order: {order.order_id}")

    except Exception as e:
        # In a real production system, you would send this to a Dead Letter Queue (DLQ)
        print(f"Error processing order: {str(e)}")
        # We don't want the function to keep retrying if the data is fundamentally broken
        return