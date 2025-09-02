from app.models.scheme import TokenRequest
from fastapi import APIRouter, Request, Depends
from app.utils.oauth_utils import generate_auth_url, exchange_code_for_tokens
from app.controller.controller import GmailClient

router = APIRouter()

# Step 1: Redirect user to Google OAuth
@router.get("/login")
def login():
    url = generate_auth_url()
    return {"auth_url": url}

# Step 2: Handle OAuth callback
@router.get("/emails/oauth2callback")
def oauth2callback(request: Request, code: str):
    tokens = exchange_code_for_tokens(code)
    return {"message": "OAuth Success. Now call /emails", "tokens": tokens}

# Step 3: Use access_token to call Gmail API

@router.post("/emails")
def get_emails(payload: TokenRequest):
    access_token = payload.access_token
    if not access_token:
        return {"error": "Not authenticated. Please login first."}
    
    gmail_client = GmailClient(access_token)


    return gmail_client.fetch_emails()
