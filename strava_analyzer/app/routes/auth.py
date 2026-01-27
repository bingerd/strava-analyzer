import logging
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
import requests

from strava_analyzer.app.config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REDIRECT_URI
from strava_analyzer.app.services.users import UserTokens, save_user_tokens, list_users, get_user_tokens
from strava_analyzer.app.services.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/authorize")
def get_authorize_url():
    """
    Redirects to Strava authorization page.
    """
    auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        "&approval_prompt=force"
        "&scope=activity:read_all"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
def auth_callback(code: str = Query(..., description="Authorization code from Strava")):
    """
    OAuth callback - exchanges authorization code for tokens and stores by athlete ID.
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
        data = response.json()

        athlete = data.get("athlete", {})
        athlete_id = athlete.get("id")

        if not athlete_id:
            raise HTTPException(status_code=400, detail="No athlete ID in response")

        athlete_name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()

        tokens = UserTokens(
            athlete_id=athlete_id,
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data.get("expires_at"),
            athlete_name=athlete_name or None,
        )
        save_user_tokens(tokens)

        logger.info(f"Authorized athlete {athlete_id} ({athlete_name})")

        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authorization Successful</title>
            <style>
                body {{ font-family: -apple-system, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
                .success {{ color: #28a745; }}
                .info {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                code {{ background: #e9ecef; padding: 2px 6px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1 class="success">Authorization Successful!</h1>
            <div class="info">
                <p><strong>Athlete:</strong> {athlete_name or 'Unknown'}</p>
                <p><strong>Athlete ID:</strong> {athlete_id}</p>
                <p><strong>Scope:</strong> {data.get('scope', 'N/A')}</p>
            </div>
            <p>Your tokens have been saved. New activities will be automatically captured via webhook.</p>
            <p><a href="/">Back to Dashboard</a></p>
        </body>
        </html>
        """)

    except requests.exceptions.HTTPError as e:
        logger.error(f"Strava API error: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Strava API error: {e.response.text}")
    except Exception as e:
        logger.error(f"Authorization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exchange")
def exchange_code(code: str = Query(..., description="Authorization code from Strava")):
    """
    Manual token exchange endpoint (alternative to callback).
    """
    return auth_callback(code)


@router.get("/users")
def get_registered_users(_: str = Depends(get_current_user)):
    """
    List all registered users (athlete IDs).
    Requires authentication.
    """
    athlete_ids = list_users()
    users = []

    for athlete_id in athlete_ids:
        tokens = get_user_tokens(athlete_id)
        if tokens:
            users.append({
                "athlete_id": athlete_id,
                "athlete_name": tokens.athlete_name,
            })

    return {"users": users, "count": len(users)}


@router.delete("/users/{athlete_id}")
def deauthorize_user(athlete_id: int, _: str = Depends(get_current_user)):
    """
    Remove a user's tokens (deauthorize).
    Requires authentication.
    """
    from strava_analyzer.app.services.users import delete_user_tokens

    if delete_user_tokens(athlete_id):
        return {"detail": f"Deauthorized athlete {athlete_id}"}
    raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")
