from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from strava_analyzer.app.config import STRAVA_VERIFY_TOKEN
from strava_analyzer.app.models.webhook import WebhookEvent

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


@router.post("/strava/webhook")
async def receive_webhook(event: WebhookEvent):
    """
    Receive Strava webhook events
    """
    print("Received event:", event.dict())

    # TODO:
    # - enqueue job
    # - fetch activity if aspect_type == "create"
    # - persist event

    return JSONResponse({"status": "ok"})
