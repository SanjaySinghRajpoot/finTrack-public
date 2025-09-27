from requests import Session
from app.db_config import SessionLocal
from app.models.scheme import TokenRequest
from fastapi import APIRouter, Request, Depends
from app.services.db_service import DBService
from app.utils.oauth_utils import generate_auth_url, exchange_code_for_tokens
from app.controller.controller import GmailClient

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
def get_emails(
    payload: TokenRequest,
    db: Session = Depends(get_db)
):
    access_token = payload.access_token
    if not access_token:
        return {"error": "Not authenticated. Please login first."}
    
    # DB service will be used in the entire api lifecycle
    db_service = DBService(db)
    
    gmail_client = GmailClient(access_token, db_service)

    # Now once we have fetched all the mails now I need to process with the help of LLMs
    # no need for this we will use free open source OCR models

    return gmail_client.fetch_emails()


