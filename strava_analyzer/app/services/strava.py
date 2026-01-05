import requests
from strava_analyzer.app.config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET
from strava_analyzer.app.storage import save_tokens, load_tokens

access_token, refresh_token = load_tokens()

def refresh_access_token():
    global access_token, refresh_token
    if not refresh_token:
        raise Exception("No refresh token available. Please authorize first via /auth/authorize")
    r = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    r.raise_for_status()
    data = r.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    save_tokens(access_token, refresh_token)
    return access_token

def get_access_token():
    global access_token
    if not access_token:
        # No token yet
        raise Exception("No access token available. Please authorize via /auth/authorize")
    try:
        r = requests.get(
            "https://www.strava.com/api/v3/athlete",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if r.status_code == 401:
            # Token expired
            return refresh_access_token()
        return access_token
    except Exception:
        return refresh_access_token()

def get_all_activities(per_page=200):
    token = get_access_token()
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

def get_activity(activity_id):
    token = get_access_token()
    r = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    r.raise_for_status()
    return r.json()
