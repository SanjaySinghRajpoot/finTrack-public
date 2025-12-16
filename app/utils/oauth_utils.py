import requests
import urllib.parse
from fastapi import Request
from typing import Optional, List
import httpx
import json
import base64

from requests import Session

from app.core.config import settings
from app.models.models import User
from app.services.jwt_service import JwtService
from app.services.subscription_service import SubscriptionService
from app.models.integration_schemas import SubscriptionCreationSchema
from app.utils.exceptions import AuthenticationError


# Use settings from centralized config
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
REDIRECT_URI = settings.OAUTH_REDIRECT_URI
GMAIL_INTEGRATION_REDIRECT_URI = settings.GMAIL_INTEGRATION_REDIRECT_URI

LOGIN_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly", 
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def generate_auth_url(scopes: Optional[List[str]] = None) -> str:
    """Generate auth URL for login flow"""
    # Validate required environment variables
    if not GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID environment variable is required")
    if not REDIRECT_URI or "None" in REDIRECT_URI:
        raise ValueError("HOST_URL environment variable is required for REDIRECT_URI")
    
    # Use provided scopes or fallback to default
    url_scopes = " ".join(scopes or LOGIN_SCOPES)
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": url_scopes,
        "access_type": "offline",  # Request refresh token
        "prompt": "consent"  # Force consent screen for refresh token
    }
    
    return f"{AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"

def generate_gmail_integration_auth_url() -> str:
    """Generate auth URL specifically for Gmail integration flow"""
    # Validate required environment variables
    if not GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID environment variable is required")
    if not GMAIL_INTEGRATION_REDIRECT_URI or "None" in GMAIL_INTEGRATION_REDIRECT_URI:
        raise ValueError("HOST_URL environment variable is required for GMAIL_INTEGRATION_REDIRECT_URI")
    
    # Use Gmail-specific scopes
    url_scopes = " ".join(GMAIL_SCOPES)
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GMAIL_INTEGRATION_REDIRECT_URI,
        "response_type": "code",
        "scope": url_scopes,
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen for refresh token
    }
    
    return f"{AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"

def generate_gmail_integration_auth_url_with_state(user_id: int) -> str:
    """Generate auth URL with user_id encoded in state parameter"""
    # Validate required environment variables
    if not GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID environment variable is required")
    if not GMAIL_INTEGRATION_REDIRECT_URI or "None" in GMAIL_INTEGRATION_REDIRECT_URI:
        raise ValueError("HOST_URL environment variable is required for GMAIL_INTEGRATION_REDIRECT_URI")
    
    # Use Gmail-specific scopes
    url_scopes = " ".join(GMAIL_SCOPES)
    
    # Encode user_id in state parameter
    state_data = {"user_id": user_id, "flow": "gmail_integration"}
    state_json = json.dumps(state_data)
    state_encoded = base64.urlsafe_b64encode(state_json.encode()).decode()
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GMAIL_INTEGRATION_REDIRECT_URI,
        "response_type": "code",
        "scope": url_scopes,
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen for refresh token
        "state": state_encoded  # Encode user_id in state
    }
    
    return f"{AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"

def decode_oauth_state(state: str) -> dict:
    """Decode the state parameter to extract user_id"""
    try:
        state_json = base64.urlsafe_b64decode(state.encode()).decode()
        return json.loads(state_json)
    except Exception as e:
        raise ValueError(f"Invalid state parameter: {str(e)}")

async def get_google_user_info(access_token: str) -> dict:
    """
    Fetch user details from Google OAuth userinfo endpoint.
    Returns the full user info dict (email, name, picture, etc).
    Raises AuthenticationError if email is missing or request fails.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            response.raise_for_status()
            user_info = response.json()
            if not user_info.get("email"):
                raise AuthenticationError("No email returned from Google")
            return user_info
    except httpx.RequestError as e:
        raise AuthenticationError(f"Failed to fetch Google user info: {str(e)}")
