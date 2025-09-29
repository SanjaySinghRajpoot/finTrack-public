import requests
import urllib.parse
from fastapi import Request
import os
from dotenv import load_dotenv

from requests import Session

from app.models.models import User
from app.services.jwt_service import JwtService

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/api/emails/oauth2callback"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

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

def exchange_code_for_tokens(code: str, db: Session):
    try:
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri":  [
            "http://localhost:8000/auth/callback",
            "http://localhost:8000/api/emails/oauth2callback"
        ],  # ✅ use one value only
            "grant_type": "authorization_code"
        }
        resp = requests.post(TOKEN_URL, data=data)
        resp.raise_for_status()
        token_data = resp.json()

        # Step 1: Get user info from Google
        user_info_resp = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        user_info_resp.raise_for_status()
        user_info = user_info_resp.json()
        email = user_info.get("email")

        if not email:
            raise ValueError("No email returned from Google")

        # Step 2: Check if user exists in DB, else create
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Step 3: Create JWT token
        jwt_service = JwtService()
        jwt_token = jwt_service.create_token(user.id, user.email)

        return {
            "jwt": jwt_token,
            "google_access_token": token_data.get('access_token'),
            "user": {"id": user.id, "email": user.email}
        }

    except requests.HTTPError as e:
        raise RuntimeError(f"Google API request failed: {e}")
    except Exception as e:
        raise RuntimeError(f"Error during auth flow: {str(e)}")