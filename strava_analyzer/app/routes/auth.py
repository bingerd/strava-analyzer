from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
import requests

from strava_analyzer.app.config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET
from strava_analyzer.app.storage import save_tokens

router = APIRouter(prefix="/auth", tags=["auth"])

AUTHORIZE_REDIRECT_URI = "http://localhost/exchange_token"  # dummy for notebook

@router.get("/authorize")
def get_authorize_url():
    """
    Returns the Strava authorization URL to visit for initial authorization.
    """
    auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={AUTHORIZE_REDIRECT_URI}"
        "&approval_prompt=force"
        "&scope=activity:read_all"
    )
    return {"url": auth_url}

@router.get("/exchange")
def exchange_code(code: str = Query(..., description="Authorization code from Strava")):
    """
    Exchange the authorization code for access + refresh tokens and store them.
    """
    try:
        response = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        tokens = response.json()
        save_tokens(tokens["access_token"], tokens["refresh_token"])
        return {"detail": "Tokens saved successfully", "scope": tokens.get("scope")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
