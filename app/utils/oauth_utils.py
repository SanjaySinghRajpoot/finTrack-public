import os
import requests
import urllib.parse
from fastapi import Request
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/api/emails/oauth2callback"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def generate_auth_url():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # so we also get refresh_token
        "prompt": "consent"
    }
    return f"{AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str):
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri":  [
            "http://localhost:8000/auth/callback",
            "http://localhost:8000/api/emails/oauth2callback"
        ],
        "grant_type": "authorization_code"
    }
    resp = requests.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    return resp.json()  # { access_token, expires_in, refresh_token, scope, token_type }
