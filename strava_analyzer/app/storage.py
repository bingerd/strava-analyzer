import json
import os

TOKEN_FILE = "tokens.json"

def save_tokens(access_token, refresh_token):
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f)

def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return None, None
    with open(TOKEN_FILE, "r") as f:
        data = json.load(f)
        return data.get("access_token"), data.get("refresh_token")
