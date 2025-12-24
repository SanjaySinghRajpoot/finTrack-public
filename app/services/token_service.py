import types
import datetime
import httpx

from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from app.core.config import settings
from app.models.models import EmailConfig, IntegrationStatus
from app.services.integration import IntegrationService
from app.services.jwt_service import JwtService
from app.services.user_service import UserService
from app.utils.oauth_utils import get_google_user_info
from app.utils.exceptions import (
    NotFoundError,
    ExternalServiceError,
    DatabaseError,
    BusinessLogicError,
    AuthenticationError
)


# Use centralized config for encryption
ENCRYPTION_KEY = settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY
fernet = Fernet(ENCRYPTION_KEY)

# Use centralized config for Google OAuth
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class TokenService:
    """
    Service responsible for token encryption/decryption and OAuth token management.
    
    Responsibilities:
    - Token encryption and decryption
    - OAuth code exchange with Google
    - Token refresh operations
    - Retrieving stored tokens
    
    Note: Integration creation/update is delegated to IntegrationService.
    """
    
    def __init__(self, db_session: Session):
        try:
            if isinstance(db_session, types.GeneratorType):
                db_session = next(db_session)
            self.db: Session = db_session
        except Exception as e:
            raise DatabaseError("Failed to initialize database session", details={"error": str(e)})

    def encrypt(self, token: str) -> str:
        """Encrypt a token string."""
        return fernet.encrypt(token.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decrypt a token string."""
        return fernet.decrypt(token.encode()).decode()

    def encrypt_tokens(self, access_token: str, refresh_token: str) -> dict:
        """Encrypt access and refresh tokens."""
        return {
            "encrypted_access": self.encrypt(access_token),
            "encrypted_refresh": self.encrypt(refresh_token),
        }

    def save_gmail_token(
            self,
            user_id: int,
            email: str,
            access_token: str,
            refresh_token: str,
            expires_in: int,
            provider: str = "gmail"
    ):
        """
        Save Gmail OAuth tokens for a user.
        
        Delegates integration creation/update to IntegrationService.
        """
        try:
            # Calculate expiration time
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

            # Encrypt tokens
            encrypted_tokens = self.encrypt_tokens(access_token, refresh_token)

            # Delegate to IntegrationService
            integration_service = IntegrationService(self.db)
            
            # Check if integration already exists
            existing_integration = integration_service.get_user_integration(user_id, provider)

            if existing_integration:
                return integration_service.update_user_integration(
                    integration=existing_integration,
                    email=email,
                    encrypted_tokens=encrypted_tokens,
                    expires_at=expires_at,
                    provider=provider
                )
            else:
                return integration_service.create_user_integration(
                    user_id=user_id,
                    email=email,
                    encrypted_tokens=encrypted_tokens,
                    expires_at=expires_at,
                    provider=provider
                )

        except Exception as e:
            # Let IntegrationService exceptions propagate
            raise e

    async def get_token(self, user_id: int, provider: str = "gmail") -> str | None:
        """Get decrypted access token for a user's integration."""
        integration_status = (
            self.db.query(IntegrationStatus)
            .filter_by(user_id=user_id, integration_type=provider)
            .first()
        )

        if not integration_status:
            return None

        email_config = (
            self.db.query(EmailConfig)
            .filter_by(integration_id=integration_status.id)
            .first()
        )

        if not email_config or not email_config.credentials:
            return None

        try:
            decrypted_access = self.decrypt(email_config.credentials.get("encrypted_access"))
            return decrypted_access
        except Exception as e:
            raise BusinessLogicError(
                f"Failed to decrypt token for user {user_id}",
                details={"provider": provider, "error": str(e)}
            )

    async def renew_google_token(self, user_id: int, provider: str = "gmail"):
        """
        Refresh a user's Google access token using the stored refresh token.
        """
        try:
            # Find the user's integration and related email config
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

            # Decrypt the refresh token
            try:
                refresh_token = self.decrypt(email_config.credentials.get("encrypted_refresh"))
            except Exception as e:
                raise BusinessLogicError(
                    f"Failed to decrypt refresh token for user {user_id}",
                    details={"error": str(e)}
                )
                
            if not refresh_token:
                raise AuthenticationError(f"Missing refresh token for user {user_id}")

            # Request new tokens from Google
            token_data = await self._refresh_google_token(refresh_token)
            
            access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            new_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

            # Update credentials in EmailConfig
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

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": new_expiry,
                "email_address": email_config.email_address,
            }

        except (NotFoundError, ExternalServiceError, DatabaseError, BusinessLogicError, AuthenticationError) as e:
            raise e
        except Exception as e:
            raise BusinessLogicError(f"Unexpected error in renew_google_token", details={"error": str(e)})

    async def _refresh_google_token(self, refresh_token: str) -> dict:
        """Request new access token from Google using refresh token."""
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
                raise ExternalServiceError(
                    "Google OAuth",
                    f"Failed to refresh token: {response.text}",
                    details={"status_code": response.status_code, "response": response.text}
                )

            return response.json()

        except httpx.RequestError as e:
            raise ExternalServiceError(
                "Google OAuth",
                f"Network error while refreshing token: {str(e)}"
            )

    async def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Exchange OAuth authorization code for tokens and create/get user.
        """
        try:
            # Exchange code for Google tokens
            token_data = await self._request_google_tokens(code)
            
            # Get user info from Google
            user_info = await get_google_user_info(token_data['access_token'])
            
            # Get or create user - call UserService directly
            user_service = UserService(self.db)
            user = user_service.get_or_create_user(user_info)
            
            # Generate JWT token - call JwtService directly
            jwt_service = JwtService()
            jwt_token = jwt_service.create_token(user.id, user.email)
            
            return {
                "jwt": jwt_token,
                "google_access_token": token_data.get('access_token'),
                "google_refresh_token": token_data.get('refresh_token'),
                "expires_in": token_data.get("expires_in"),
                "user": user_info
            }
            
        except (ExternalServiceError, AuthenticationError, DatabaseError) as e:
            raise e
        except Exception as e:
            raise BusinessLogicError(
                "Unexpected error during OAuth token exchange",
                details={"error": str(e)}
            )

    async def handleGmailToken(self, code: str) -> dict:
        """Exchange authorization code for Gmail tokens (login flow)."""
        try: 
            return await self._request_google_tokens(code)
        except Exception as e:
            raise e

    async def handleGmailIntegrationToken(self, code: str) -> dict:
        """Exchange authorization code for Gmail integration tokens."""
        try: 
            return await self._request_google_tokens_for_integration(code)
        except Exception as e:
            raise e

    async def _request_google_tokens(self, code: str) -> dict:
        """Request tokens from Google using authorization code (login flow)."""
        return await self._exchange_code_with_google(
            code=code,
            redirect_uri=settings.OAUTH_REDIRECT_URI
        )

    async def _request_google_tokens_for_integration(self, code: str) -> dict:
        """Request tokens from Google using authorization code (integration flow)."""
        return await self._exchange_code_with_google(
            code=code,
            redirect_uri=settings.GMAIL_INTEGRATION_REDIRECT_URI
        )

    async def _exchange_code_with_google(self, code: str, redirect_uri: str) -> dict:
        """Common method to exchange authorization code with Google."""
        try:
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




