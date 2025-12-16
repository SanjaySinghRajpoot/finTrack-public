"""Gmail Integration Service"""

from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import IntegrationStatus, IntegrationState, EmailConfig
from app.services.token_service import TokenService
from app.services.integration.base_integration_service import BaseIntegrationService
from app.utils.oauth_utils import generate_gmail_integration_auth_url_with_state, GMAIL_SCOPES, GOOGLE_USERINFO_URL, get_google_user_info
from app.utils.exceptions import (
    NotFoundError,
    BusinessLogicError,
    DatabaseError,
    AuthenticationError
)


class GmailIntegrationService(BaseIntegrationService):
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.token_service = TokenService(db)
    
    @property
    def integration_slug(self) -> str:
        return "gmail"
    
    @property
    def integration_display_name(self) -> str:
        return "Gmail"
    
    async def link_integration(self, user: dict) -> Dict[str, str]:
        try:
            user_id = self._validate_user(user)
            auth_url = generate_gmail_integration_auth_url_with_state(user_id)
            
            return {
                "auth_url": auth_url,
                "message": "Please authorize Gmail access to continue",
                "provider": self.integration_slug
            }
            
        except Exception as e:
            self._handle_error("generate authorization URL", e)
    
    async def oauth_callback(self, code: str, user: dict) -> Dict[str, Any]:
        try:
            user_id = self._validate_user(user)
            
            token_data = await self.token_service.handleGmailIntegrationToken(code)
            
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            
            if not access_token or not refresh_token:
                raise AuthenticationError("Invalid token response from Google")
            
            user_info = await get_google_user_info(access_token)
            gmail_email = user_info.get("email")
            
            email_config = self.token_service.save_gmail_token(
                user_id=user_id,
                email=gmail_email,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                provider=self.integration_slug
            )
            
            return {
                "success": True,
                "message": f"{self.integration_display_name} integration linked successfully",
                "integration": {
                    "email": gmail_email,
                    "provider": self.integration_slug,
                    "connected_at": datetime.utcnow().isoformat(),
                    "expires_at": email_config.expires_at.isoformat() if email_config.expires_at else None,
                    "user_info": user_info
                }
            }
            
        except (AuthenticationError, DatabaseError) as e:
            raise e
        except Exception as e:
            self._handle_error("complete OAuth callback", e)
    
    def _cleanup_integration_data(self, integration_status: IntegrationStatus) -> None:
        if integration_status.email_config:
            self.db.delete(integration_status.email_config)
