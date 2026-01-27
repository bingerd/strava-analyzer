import json
import logging
from datetime import datetime
from google.cloud import storage
from strava_analyzer.app.config import GCS_BUCKET_NAME

logger = logging.getLogger(__name__)

_client = None


def get_gcs_client():
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def upload_activity(activity_id: int, activity_data: dict, owner_id: int | None = None) -> str:
    """
    Upload activity data to GCS as JSON.

    Path format: activities/{owner_id}/{YYYY}/{MM}/{activity_id}.json
    """
    client = get_gcs_client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    start_date = activity_data.get("start_date", datetime.utcnow().isoformat())
    try:
        dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.utcnow()

    # Organize by owner_id for multi-user support
    if owner_id:
        blob_path = f"activities/{owner_id}/{dt.year}/{dt.month:02d}/{activity_id}.json"
    else:
        blob_path = f"activities/{dt.year}/{dt.month:02d}/{activity_id}.json"

    blob = bucket.blob(blob_path)

    blob.upload_from_string(
        json.dumps(activity_data, indent=2),
        content_type="application/json"
    )

    logger.info(f"Uploaded activity {activity_id} to gs://{GCS_BUCKET_NAME}/{blob_path}")
    return f"gs://{GCS_BUCKET_NAME}/{blob_path}"


def upload_webhook_event(event_data: dict) -> str:
    """
    Upload raw webhook event to GCS for auditing.

    Path format: webhooks/{YYYY}/{MM}/{DD}/{timestamp}_{object_id}.json
    """
    client = get_gcs_client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    now = datetime.utcnow()
    object_id = event_data.get("object_id", "unknown")
    timestamp = now.strftime("%H%M%S%f")

    blob_path = f"webhooks/{now.year}/{now.month:02d}/{now.day:02d}/{timestamp}_{object_id}.json"
    blob = bucket.blob(blob_path)

    blob.upload_from_string(
        json.dumps(event_data, indent=2),
        content_type="application/json"
    )

    logger.info(f"Uploaded webhook event to gs://{GCS_BUCKET_NAME}/{blob_path}")
    return f"gs://{GCS_BUCKET_NAME}/{blob_path}"
