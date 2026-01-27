import logging
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from strava_analyzer.app.config import STRAVA_VERIFY_TOKEN
from strava_analyzer.app.models.webhook import WebhookEvent
from strava_analyzer.app.services.strava import get_activity_for_user
from strava_analyzer.app.services.gcs import upload_activity, upload_webhook_event
from strava_analyzer.app.services.users import get_user_tokens, delete_user_tokens

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/strava/webhook")
async def verify_webhook(request: Request):
    """
    Strava verification handshake
    """
    mode = request.query_params.get("hub.mode")
    challenge = request.query_params.get("hub.challenge")
    token = request.query_params.get("hub.verify_token")

    if mode == "subscribe" and token == STRAVA_VERIFY_TOKEN:
        return JSONResponse({"hub.challenge": challenge})

    raise HTTPException(status_code=403, detail="Verification failed")


def process_activity_event(event_data: dict):
    """
    Background task to fetch activity data and store in GCS.
    Uses owner_id from webhook to identify which user's tokens to use.
    """
    try:
        upload_webhook_event(event_data)

        object_type = event_data.get("object_type")
        aspect_type = event_data.get("aspect_type")
        object_id = event_data.get("object_id")
        owner_id = event_data.get("owner_id")

        if object_id is None or owner_id is None:
            logger.warning(f"Received webhook event without object_id or owner_id: {event_data}")
            return

        # Handle athlete deauthorization
        if object_type == "athlete" and aspect_type == "delete":
            logger.info(f"Athlete {owner_id} deauthorized the app")
            delete_user_tokens(owner_id)
            return

        # Check if we have tokens for this user
        tokens = get_user_tokens(owner_id)
        if tokens is None:
            logger.warning(f"No tokens found for athlete {owner_id}, skipping activity {object_id}")
            return

        if object_type == "activity" and aspect_type == "create":
            logger.info(f"Fetching new activity {object_id} for athlete {owner_id}")
            activity_data = get_activity_for_user(owner_id, object_id)
            gcs_path = upload_activity(object_id, activity_data, owner_id=owner_id)
            logger.info(f"Activity {object_id} stored at {gcs_path}")

        elif object_type == "activity" and aspect_type == "update":
            logger.info(f"Fetching updated activity {object_id} for athlete {owner_id}")
            activity_data = get_activity_for_user(owner_id, object_id)
            gcs_path = upload_activity(object_id, activity_data, owner_id=owner_id)
            logger.info(f"Updated activity {object_id} stored at {gcs_path}")

        elif object_type == "activity" and aspect_type == "delete":
            logger.info(f"Activity {object_id} was deleted by athlete {owner_id}")
            # Optionally: delete from GCS or mark as deleted

    except Exception as e:
        logger.error(f"Error processing webhook event: {e}", exc_info=True)


@router.post("/strava/webhook")
async def receive_webhook(event: WebhookEvent, background_tasks: BackgroundTasks):
    """
    Receive Strava webhook events.

    Immediately returns 200 OK (required by Strava within 2 seconds),
    then processes the activity in the background.
    """
    logger.info(
        f"Received webhook: object_type={event.object_type}, "
        f"aspect_type={event.aspect_type}, object_id={event.object_id}, "
        f"owner_id={event.owner_id}"
    )

    background_tasks.add_task(process_activity_event, event.model_dump())

    return JSONResponse({"status": "ok"})
