from datetime import datetime
import os
from app.models.models import ProcessedEmailData
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Load client secrets from Google Cloud Console
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = "http://localhost:8000/api/emails/oauth2callback"

class GmailOAuth:
    """Handles OAuth flow for Gmail."""

    @staticmethod
    def get_flow():
        """Create OAuth2 flow instance."""
        return Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

    @staticmethod
    def build_service(token_data: dict):
        """Build Gmail service from token data."""
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        return build("gmail", "v1", credentials=creds)


def create_processed_email_data(user_id: int, email_id: int, data: dict) -> ProcessedEmailData:
    """
    Creates a ProcessedEmailData object from the given dictionary and saves it to the DB.
    
    :param session: SQLAlchemy session
    :param user_id: ID of the user owning the email
    :param email_id: ID of the source email
    :param data: Dictionary containing document information
    :return: ProcessedEmailData instance
    """
    def parse_date(date_str):
        if date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        return None

    processed_data = ProcessedEmailData(
        user_id=user_id,
        email_id=email_id,
        document_type=data.get("document_type"),
        title=data.get("title"),
        description=data.get("description"),
        document_number=data.get("document_number"),
        reference_id=data.get("reference_id"),
        issue_date=parse_date(data.get("issue_date")),
        due_date=parse_date(data.get("due_date")),
        payment_date=parse_date(data.get("payment_date")),
        amount=data.get("amount", 0.0),
        currency=data.get("currency", "INR"),
        is_paid=data.get("is_paid", False),
        payment_method=data.get("payment_method"),
        vendor_name=data.get("vendor_name"),
        vendor_gstin=data.get("vendor_gstin"),
        category=data.get("category"),
        tags=data.get("tags"),
        meta_data=data.get("metadata"),  # optional extra metadata
        file_url=data.get("file_url")
    )

    return processed_data
