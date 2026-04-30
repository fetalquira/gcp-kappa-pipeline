import base64
import json
import logging
import traceback
import os
from google.cloud import firestore
from pydantic import ValidationError
from schemas import OrderModel 

# Set up structured logging to bypass GCP's audit noise
logging.basicConfig(level=logging.INFO)

# Global initialization for warm-start speed
DB_NAME = os.getenv("TARGET_DB_NAME", "(default)")
db = firestore.Client(database=DB_NAME)

def process_order(event, context):
    """
    Triggered by a message on a Cloud Pub/Sub topic.
    """
    try:
        # 1. Decode safely INSIDE the blast shield
        if 'data' not in event:
            raise ValueError("Payload missing 'data' key.")
            
        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        data_json = json.loads(pubsub_message)
        logging.info(f"Incoming payload: {data_json}")

        # 2. Validate using Pydantic
        order = OrderModel(**data_json)
        
        # 3. Write to Firestore idempotently
        doc_ref = db.collection("orders").document(str(order.transaction_id))
        doc_ref.set(order.model_dump(mode='json'))

        logging.info(f"SUCCESS: Order {order.transaction_id} persisted to Firestore.")

    except ValidationError as e:
        # THE DATA IS BAD: Log it, but DO NOT retry. 
        # Returning tells Pub/Sub to drop the message from the queue.
        logging.error(f"SCHEMA_ERROR: Invalid payload format.\n{e}")
        return 

    except Exception as e:
        # THE SYSTEM FAILED: Network error, missing keys, etc.
        # Log the exact line of failure, then RAISE to trigger a Pub/Sub retry.
        error_stack = traceback.format_exc()
        logging.error(f"CRITICAL_FAILURE: {str(e)}\n{error_stack}")
        raise e