import types

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
import datetime
import requests
import httpx
import asyncio

from app.models.models import Email, EmailConfig, IntegrationStatus, IntegrationState
import os
from dotenv import load_dotenv
load_dotenv()

# Encryption key (should be stored securely, e.g., in env variables)
ENCRYPTION_KEY = b'X1Tz1y9Ff0QZxQ9fDd0tKXk8h1u4z6pF8H2xG4XK9sY='
fernet = Fernet(ENCRYPTION_KEY)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

class TokenService:
    def __init__(self, db_session: Session):
        try:
            if isinstance(db_session, types.GeneratorType):
                db_session = next(db_session)
            self.db: Session = db_session
        except Exception as e:
            raise e

    def encrypt(self, token: str) -> str:
        return fernet.encrypt(token.encode()).decode()

    def decrypt(self, token: str) -> str:
        return fernet.decrypt(token.encode()).decode()

    def _get_integration(self, user_id: int, provider: str):
        """Fetch existing integration if present."""
        return (
            self.db.query(IntegrationStatus)
            .filter_by(user_id=user_id, integration_type=provider)
            .first()
        )

    # In a similar way we will have functions to save other tokens as well
    def save_gmail_token(
            self,
            user_id: int,
            email: str,
            access_token: str,
            refresh_token: str,
            expires_in: int,
            provider: str = "gmail"
    ):
        try:
            # Calculate expiration time
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

            # Encrypt tokens
            encrypted_tokens = self._encrypt_tokens(access_token, refresh_token)

            # Check if integration already exists
            integration = self._get_integration(user_id, provider)

            # If integration exists, update its tokens
            if integration:
                return self._update_existing_integration(integration, email, encrypted_tokens, expires_at, provider)
            else:
                return self._create_new_integration(user_id, email, encrypted_tokens, expires_at, provider)

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Save gmail token: {str(e)}")

    def _create_email_config(self, email: str, integration_id: int, tokens: dict, expires_at, provider: str):
        """Create new EmailConfig linked to integration."""
        email_config = EmailConfig(
            email_address=email,
            integration_id=integration_id,
            provider=provider,
            expires_at=expires_at,
            credentials=tokens,
        )

        self.db.add(email_config)
        self.db.commit()
        return email_config

    def _create_new_integration(self, user_id: int, email: str, tokens: dict, expires_at, provider: str):
        """Create a new integration and linked email config."""
        integration = IntegrationStatus(
            user_id=user_id,
            integration_type=provider,
            status=IntegrationState.connected,
            sync_interval_minutes=600,
        )

        self.db.add(integration)
        self.db.commit()  # Commit to get the ID

        return self._create_email_config(email, integration.id, tokens, expires_at, provider)

    def _encrypt_tokens(self, access_token: str, refresh_token: str) -> dict:
        """Encrypt access and refresh tokens."""
        return {
            "encrypted_access": self.encrypt(access_token),
            "encrypted_refresh": self.encrypt(refresh_token),
        }

    def _update_existing_integration(self, integration, email: str, tokens: dict, expires_at, provider: str):
        """Update tokens if integration already exists."""
        email_config = (
            self.db.query(EmailConfig)
            .filter_by(integration_id=integration.id, provider=provider)
            .first()
        )

        if email_config:
            email_config.credentials = tokens
            email_config.expires_at = expires_at
            email_config.email_address = email
            self.db.commit()
            return email_config

        # If Integration exists but EmailConfig missing, create it
        return self._create_email_config(email, integration.id, tokens, expires_at, provider)

    def get_token(self, user_id: int, provider: str = "gmail") -> str | None:
        """
        Retrieve and decrypt stored Gmail tokens for a given user.
        Returns a dict with access and refresh tokens, or None if not found.
        """

        # Step 1: Find integration for the given user and provider
        integration_status = (
            self.db.query(IntegrationStatus)
            .filter_by(user_id=user_id, integration_type=provider)
            .first()
        )

        if not integration_status:
            return None

        # Step 2: Find the associated EmailConfig record
        email_config = (
            self.db.query(EmailConfig)
            .filter_by(integration_id=integration_status.id)
            .first()
        )

        if not email_config or not email_config.credentials:
            return None

        # Step 3: Extract and decrypt tokens
        token_data = email_config.credentials
        decrypted_access = self.decrypt(token_data.get("encrypted_access"))

        return decrypted_access

    async def renew_google_token(self, user_id: int, provider: str = "gmail"):
        """
        Refresh a user's Google access token using the refresh token stored in EmailConfig.
        Updates the EmailConfig record with the new encrypted access token and expiry time.
        """
        try:
            # Step 1: Find the user's integration and related email config
            integration_status = (
                self.db.query(IntegrationStatus)
                .filter_by(user_id=user_id, integration_type=provider)
                .first()
            )
            if not integration_status:
                raise Exception(f"No integration found for user {user_id}")

            email_config = (
                self.db.query(EmailConfig)
                .filter_by(integration_id=integration_status.id)
                .first()
            )
            if not email_config or not email_config.credentials:
                raise Exception(f"No email config found for user {user_id}")

            # Step 2: Decrypt the refresh token
            refresh_token = self.decrypt(email_config.credentials.get("encrypted_refresh"))
            if not refresh_token:
                raise Exception(f"Missing refresh token for user {user_id}")

            # Step 3: Request new tokens from Google
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=10.0,
                )

            if response.status_code != 200:
                raise Exception(f"Failed to refresh token: {response.text}")

            data = response.json()
            access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            new_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

            # Step 4: Encrypt and update credentials in EmailConfig
            encrypted_access = self.encrypt(access_token)
            email_config.credentials["encrypted_access"] = encrypted_access
            email_config.expires_at = new_expiry
            email_config.updated_at = datetime.datetime.utcnow()

            self.db.add(email_config)
            self.db.commit()

            # Step 5: Return updated token data
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": new_expiry,
                "email_address": email_config.email_address,
            }

        except httpx.RequestError as e:
            raise Exception(f"Network error while refreshing token: {str(e)}")

        except Exception as e:
            raise Exception(f"Unexpected error in renew_google_token: {str(e)}")
