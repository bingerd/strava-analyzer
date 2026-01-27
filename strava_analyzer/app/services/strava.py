import logging
import time
import requests
from typing import Optional
from strava_analyzer.app.config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET
from strava_analyzer.app.services.users import UserTokens, get_user_tokens, save_user_tokens

logger = logging.getLogger(__name__)


class StravaClient:
    """Strava API client for a specific user."""

    def __init__(self, athlete_id: int):
        self.athlete_id = athlete_id
        self._tokens: Optional[UserTokens] = None

    def _load_tokens(self) -> UserTokens:
        if self._tokens is None:
            self._tokens = get_user_tokens(self.athlete_id)
        if self._tokens is None:
            raise Exception(f"No tokens found for athlete {self.athlete_id}. User needs to authorize.")
        return self._tokens

    def _refresh_tokens(self) -> str:
        tokens = self._load_tokens()

        r = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
            },
        )
        r.raise_for_status()
        data = r.json()

        self._tokens = UserTokens(
            athlete_id=self.athlete_id,
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data.get("expires_at"),
            athlete_name=tokens.athlete_name,
        )
        save_user_tokens(self._tokens)
        logger.info(f"Refreshed tokens for athlete {self.athlete_id}")

        return self._tokens.access_token

    def get_access_token(self) -> str:
        tokens = self._load_tokens()

        # Check if token is expired
        if tokens.expires_at and tokens.expires_at < time.time():
            return self._refresh_tokens()

        # Verify token is still valid
        r = requests.get(
            "https://www.strava.com/api/v3/athlete",
            headers={"Authorization": f"Bearer {tokens.access_token}"}
        )
        if r.status_code == 401:
            return self._refresh_tokens()

        return tokens.access_token

    def get_activity(self, activity_id: int) -> dict:
        token = self.get_access_token()
        r = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        r.raise_for_status()
        return r.json()

    def get_all_activities(self, per_page: int = 200) -> list[dict]:
        token = self.get_access_token()
        activities = []
        page = 1

        while True:
            r = requests.get(
                "https://www.strava.com/api/v3/athlete/activities",
                headers={"Authorization": f"Bearer {token}"},
                params={"per_page": per_page, "page": page}
            )
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            activities.extend(data)
            page += 1

        return activities


# Convenience functions for backward compatibility and simple use cases
def get_activity_for_user(athlete_id: int, activity_id: int) -> dict:
    """Fetch a specific activity for a user."""
    client = StravaClient(athlete_id)
    return client.get_activity(activity_id)


def get_all_activities_for_user(athlete_id: int) -> list[dict]:
    """Fetch all activities for a user."""
    client = StravaClient(athlete_id)
    return client.get_all_activities()
