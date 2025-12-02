import types

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
import datetime
import httpx
import asyncio

from app.models.models import Email, EmailConfig, IntegrationStatus, IntegrationState, Integration, User
from app.services.db_service import DBService
from app.services.integration import IntegrationService
from app.services.subscription_service import SubscriptionService
from app.services.jwt_service import JwtService
from app.services.user_service import UserService
from app.models.integration_schemas import CreditDeductionSchema, SubscriptionCreationSchema
from app.utils.oauth_utils import GOOGLE_USERINFO_URL, get_google_user_info
from app.utils.exceptions import (
    NotFoundError,
    ExternalServiceError,
    DatabaseError,
    SubscriptionError,
    BusinessLogicError,
    AuthenticationError
)
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
            raise DatabaseError("Failed to initialize database session", details={"error": str(e)})

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

        except (SubscriptionError, NotFoundError, BusinessLogicError) as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to save gmail token", details={"error": str(e)})

    def _create_email_config(self, email: str, integration_id: int, tokens: dict, expires_at, provider: str):
        """Create new EmailConfig linked to integration."""
        try:
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
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to create email config", details={"error": str(e)})

    def _create_new_integration(self, user_id: int, email: str, tokens: dict, expires_at, provider: str):
        """Create a new integration and linked email config with feature validation."""
        try:
            # Initialize services
            integration_service = IntegrationService(self.db)
            subscription_service = SubscriptionService(self.db)
            
            # Get the master integration record
            master_integration = integration_service.get_integration_by_slug(provider)
            if not master_integration:
                raise NotFoundError("Integration", provider, details={"provider": provider})
            
            # Check if user can use this integration (validate subscription and credits)
            primary_feature_key = f"{provider.upper()}_SYNC"  # e.g., GMAIL_SYNC
            validation = subscription_service.validate_credits_for_feature(user_id, primary_feature_key)
            
            if not validation.valid:
                raise SubscriptionError(f"Cannot create integration: {validation.message}", 
                                      details={"feature": primary_feature_key, "validation": validation.model_dump()})
            
            # Create the integration status
            integration = IntegrationStatus(
                user_id=user_id,
                integration_type=provider,
                integration_master_id=master_integration.id,  # Link to master integration
                status=IntegrationState.connected,
                sync_interval_minutes=600,
            )

            self.db.add(integration)
            self.db.commit()  # Commit to get the ID

            # Create email config
            email_config = self._create_email_config(email, integration.id, tokens, expires_at, provider)
            
            # Deduct credits for initial setup
            try:
                credit_result: CreditDeductionSchema = subscription_service.deduct_credits_for_feature(user_id, primary_feature_key)
                if not credit_result.success:
                    # Log warning but don't fail the integration creation
                    print(f"Warning: Could not deduct credits for {primary_feature_key}: {credit_result.error}")
            except Exception as credit_error:
                print(f"Warning: Credit deduction failed: {credit_error}")
            
            return email_config
            
        except (NotFoundError, SubscriptionError) as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to create integration", details={"error": str(e)})

    def _encrypt_tokens(self, access_token: str, refresh_token: str) -> dict:
        """Encrypt access and refresh tokens."""
        return {
            "encrypted_access": self.encrypt(access_token),
            "encrypted_refresh": self.encrypt(refresh_token),
        }

    def _update_existing_integration(self, integration, email: str, tokens: dict, expires_at, provider: str):
        """Update tokens if integration already exists with feature validation."""
        try:
            # Initialize services
            integration_service = IntegrationService(self.db)
            subscription_service = SubscriptionService(self.db)
            
            # Ensure integration is linked to master integration
            if not integration.integration_master_id:
                master_integration = integration_service.get_integration_by_slug(provider)
                if master_integration:
                    integration.integration_master_id = master_integration.id
            
            # Check if user can still use this integration
            primary_feature_key = f"{provider.upper()}_SYNC"
            validation = subscription_service.validate_credits_for_feature(integration.user_id, primary_feature_key)
            
            if not validation.valid:
                # Update integration status to indicate credit issues
                integration.status = IntegrationState.error
                integration.error_message = f"Integration paused: {validation.message}"
                self.db.commit()
                raise SubscriptionError(f"Cannot update integration: {validation.message}", 
                                      details={"feature": primary_feature_key, "validation": validation.model_dump()})
            
            # Update integration status to connected and clear any errors
            integration.status = IntegrationState.connected
            integration.error_message = None
            integration.updated_at = datetime.datetime.utcnow()
            
            email_config = (
                self.db.query(EmailConfig)
                .filter_by(integration_id=integration.id, provider=provider)
                .first()
            )

            if email_config:
                # Update existing email config
                email_config.credentials = tokens
                email_config.expires_at = expires_at
                email_config.email_address = email
                email_config.updated_at = datetime.datetime.utcnow()
                self.db.commit()
                return email_config

            # If Integration exists but EmailConfig missing, create it
            email_config = self._create_email_config(email, integration.id, tokens, expires_at, provider)
            
            # Ensure integration status is updated after creating email config
            self.db.commit()
            
            return email_config
            
        except SubscriptionError as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(f"Failed to update integration", details={"error": str(e)})

    async def get_token(self, user_id: int, provider: str = "gmail") -> str | None:
        """
        Retrieve and decrypt stored Gmail tokens for a given user.
        Returns a dict with access and refresh tokens, or None if not found.
        """
        # Direct DB queries (sync) - no executor needed
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
        try:
            decrypted_access = self.decrypt(token_data.get("encrypted_access"))
            return decrypted_access
        except Exception as e:
            raise BusinessLogicError(f"Failed to decrypt token for user {user_id}", 
                                   details={"provider": provider, "error": str(e)})

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
                raise NotFoundError("Integration", f"user_id:{user_id}, provider:{provider}")

            email_config = (
                self.db.query(EmailConfig)
                .filter_by(integration_id=integration_status.id)
                .first()
            )
            if not email_config or not email_config.credentials:
                raise NotFoundError("Email configuration", f"integration_id:{integration_status.id}")

            # Step 2: Decrypt the refresh token
            try:
                refresh_token = self.decrypt(email_config.credentials.get("encrypted_refresh"))
            except Exception as e:
                raise BusinessLogicError(f"Failed to decrypt refresh token for user {user_id}", 
                                       details={"error": str(e)})
                
            if not refresh_token:
                raise AuthenticationError(f"Missing refresh token for user {user_id}")

            # Step 3: Request new tokens from Google using async httpx
            try:
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
                    raise ExternalServiceError("Google OAuth", 
                                             f"Failed to refresh token: {response.text}",
                                             details={"status_code": response.status_code, "response": response.text})

                data = response.json()
                access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                new_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

            except httpx.RequestError as e:
                raise ExternalServiceError("Google OAuth", 
                                         f"Network error while refreshing token: {str(e)}")

            # Step 4: Encrypt and update credentials in EmailConfig
            try:
                encrypted_access = self.encrypt(access_token)
                email_config.credentials["encrypted_access"] = encrypted_access
                email_config.expires_at = new_expiry
                email_config.updated_at = datetime.datetime.utcnow()

                self.db.add(email_config)
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                raise DatabaseError("Failed to update token credentials", details={"error": str(e)})

            # Step 5: Return updated token data
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": new_expiry,
                "email_address": email_config.email_address,
            }

        except (NotFoundError, ExternalServiceError, DatabaseError, BusinessLogicError, AuthenticationError) as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            raise BusinessLogicError(f"Unexpected error in renew_google_token", details={"error": str(e)})

    async def exchange_code_for_tokens(self, code: str) -> dict:
        try:
            # Step 1: Exchange code for Google tokens (async)
            token_data = await self._request_google_tokens(code)
            
            # Step 2: Get user info from Google (async)
            user_info = await get_google_user_info(token_data['access_token'])
            
            # Step 3: Get or create user in database (sync DB operation)
            user = self._get_or_create_user(user_info)
            
            # Step 4: Generate JWT token
            jwt_token = self._generate_jwt_token(user.id, user.email)
            
            return {
                "jwt": jwt_token,
                "google_access_token": token_data.get('access_token'),
                "google_refresh_token": token_data.get('refresh_token'),
                "expires_in": token_data.get("expires_in"),
                "user": user_info
            }
            
        except (ExternalServiceError, AuthenticationError, DatabaseError) as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            raise BusinessLogicError(
                "Unexpected error during OAuth token exchange",
                details={"error": str(e)}
            )

    async def handleGmailToken(self, code: str) -> dict:
        try: 
            token_data = await self._request_google_tokens(code)
             
            return token_data

        except Exception as e:
            raise e

    async def handleGmailIntegrationToken(self, code: str) -> dict:
        """
        Exchange authorization code for tokens using Gmail integration redirect URI.
        This is separate from the login flow which uses a different redirect URI.
        """
        try: 
            token_data = await self._request_google_tokens_for_integration(code)
             
            return token_data

        except Exception as e:
            raise e

    async def _request_google_tokens(self, code: str) -> dict:
        """Async token request using httpx"""
        try:
            # Get the redirect URI from environment - must match the one used in the auth URL
            redirect_uri = os.getenv("HOST_URL", "https://fintrack.rapidlabs.app") + "/api/emails/oauth2callback"
            
            data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(GOOGLE_TOKEN_URL, data=data, timeout=10)
            
            if response.status_code != 200:
                raise ExternalServiceError(
                    "Google OAuth",
                    f"Token request failed: {response.text}",
                    details={"status_code": response.status_code}
                )
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(
                "Google OAuth",
                f"Token request failed: {e.response.text if e.response else str(e)}",
                details={"status_code": e.response.status_code if e.response else None}
            )
        except httpx.RequestError as e:
            raise ExternalServiceError(
                "Google OAuth",
                f"Network error during token request: {str(e)}"
            )

    async def _request_google_tokens_for_integration(self, code: str) -> dict:
        """
        Request Google tokens using the Gmail integration redirect URI (async).
        This is separate from the login flow.
        """
        try:
            # Use the Gmail integration redirect URI
            redirect_uri = os.getenv("HOST_URL", "https://fintrack.rapidlabs.app") + "/api/integration/gmail/callback"
            
            data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(GOOGLE_TOKEN_URL, data=data, timeout=10)
            
            if response.status_code != 200:
                raise ExternalServiceError(
                    "Google OAuth",
                    f"Token request failed: {response.text}",
                    details={"status_code": response.status_code}
                )
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(
                "Google OAuth",
                f"Token request failed: {e.response.text if e.response else str(e)}",
                details={"status_code": e.response.status_code if e.response else None}
            )
        except httpx.RequestError as e:
            raise ExternalServiceError(
                "Google OAuth",
                f"Network error during token request: {str(e)}"
            )

    def _get_or_create_user(self, user_info: dict) -> User:
        user_service = UserService(self.db)
        return user_service.get_or_create_user(user_info)

    def _generate_jwt_token(self, user_id: int, email: str) -> str:
        jwt_service = JwtService()
        return jwt_service.create_token(user_id, email)
