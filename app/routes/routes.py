from requests import Session
from app.db_config import SessionLocal
from app.middleware.auth_middleware import jwt_middleware
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

@router.get("/login")
def login():
    url = generate_auth_url()
    return {"auth_url": url}

@router.get("/emails/oauth2callback")
def oauth2callback(request: Request, code: str, db: Session = Depends(get_db)):
    tokens = exchange_code_for_tokens(code, db)
    return tokens

@router.post("/emails")
def get_emails(
    payload: TokenRequest,
    db: Session = Depends(get_db)
):
    try:
        access_token = payload.access_token
        if not access_token:
            return {"error": "Not authenticated. Please login first."}

        db_service = DBService(db)

        gmail_client = GmailClient(access_token, db_service)

        return gmail_client.fetch_emails()
    except Exception as e:
        return e

@router.get("/payment/info")
def get_payment_info(user=Depends(jwt_middleware)):
    try:
        user_id = user.get("user_id")

        print(user_id)
    except Exception as e:
        return e
