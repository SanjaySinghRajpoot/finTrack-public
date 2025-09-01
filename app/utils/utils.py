import os
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
