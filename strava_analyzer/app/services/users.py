import json
import logging
from dataclasses import dataclass
from typing import Optional
from google.cloud import storage
from google.cloud.exceptions import NotFound
from strava_analyzer.app.config import GCS_BUCKET_NAME

logger = logging.getLogger(__name__)

_client = None


def get_gcs_client():
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


@dataclass
class UserTokens:
    athlete_id: int
    access_token: str
    refresh_token: str
    expires_at: Optional[int] = None
    athlete_name: Optional[str] = None


def get_user_tokens(athlete_id: int) -> Optional[UserTokens]:
    """
    Retrieve tokens for a specific athlete from GCS.
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"users/{athlete_id}/tokens.json")

        data = json.loads(blob.download_as_string())
        return UserTokens(
            athlete_id=data["athlete_id"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data.get("expires_at"),
            athlete_name=data.get("athlete_name"),
        )
    except NotFound:
        logger.warning(f"No tokens found for athlete {athlete_id}")
        return None
    except Exception as e:
        logger.error(f"Error loading tokens for athlete {athlete_id}: {e}")
        return None


def save_user_tokens(tokens: UserTokens) -> None:
    """
    Save tokens for a specific athlete to GCS.
    """
    client = get_gcs_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f"users/{tokens.athlete_id}/tokens.json")

    data = {
        "athlete_id": tokens.athlete_id,
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "expires_at": tokens.expires_at,
        "athlete_name": tokens.athlete_name,
    }

    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json"
    )
    logger.info(f"Saved tokens for athlete {tokens.athlete_id}")


def delete_user_tokens(athlete_id: int) -> bool:
    """
    Delete tokens for a specific athlete (for deauthorization).
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"users/{athlete_id}/tokens.json")
        blob.delete()
        logger.info(f"Deleted tokens for athlete {athlete_id}")
        return True
    except NotFound:
        return False
    except Exception as e:
        logger.error(f"Error deleting tokens for athlete {athlete_id}: {e}")
        return False


def list_users() -> list[int]:
    """
    List all registered athlete IDs.
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blobs = bucket.list_blobs(prefix="users/")

        athlete_ids = set()
        for blob in blobs:
            parts = blob.name.split("/")
            if len(parts) >= 2 and parts[1].isdigit():
                athlete_ids.add(int(parts[1]))

        return sorted(athlete_ids)
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return []
