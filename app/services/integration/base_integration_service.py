"""
Base Integration Service

Provides abstract base class for all integration services.
Each integration should extend this class to implement their specific OAuth flow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.models import IntegrationStatus, IntegrationState
from app.services.integration.service import IntegrationService
from app.utils.exceptions import (
    NotFoundError,
    BusinessLogicError,
    DatabaseError,
    AuthenticationError
)


class BaseIntegrationService(ABC):
    
    def __init__(self, db: Session):
        self.db = db
        self.integration_service = IntegrationService(db)
    
    @property
    @abstractmethod
    def integration_slug(self) -> str:
        """Return integration slug (e.g., 'gmail', 'whatsapp')"""
        pass
    
    @property
    @abstractmethod
    def integration_display_name(self) -> str:
        """Return human-readable integration name"""
        pass
    
    @abstractmethod
    async def link_integration(self, user: dict) -> Dict[str, Any]:
        """
        Initiate integration linking process.
        
        Should return OAuth URL for OAuth-based integrations,
        or instructions for manual setup.
        """
        pass
    
    async def oauth_callback(self, code: str, user: dict) -> Dict[str, Any]:
        pass
    
    async def delink_integration(self, user: dict) -> Dict[str, str]:
        """
        Delink integration by removing tokens and marking as disconnected.
        Uses template method pattern - calls abstract _cleanup_integration_data.
        """
        try:
            user_id = user.get("user_id")
            
            integration_status = self._get_integration_status(user_id)
            
            if not integration_status:
                raise NotFoundError(
                    f"{self.integration_display_name} Integration",
                    f"user_id:{user_id}",
                    details={"message": f"No {self.integration_display_name} integration found for this user"}
                )
            
            self._cleanup_integration_data(integration_status)
            
            integration_status.status = IntegrationState.disconnected
            integration_status.error_message = "Integration manually disconnected by user"
            integration_status.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"{self.integration_display_name} integration delinked successfully",
                "provider": self.integration_slug
            }
            
        except NotFoundError as e:
            raise e
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(
                f"Failed to delink {self.integration_display_name} integration",
                details={"error": str(e)}
            )
    
    def _get_integration_status(self, user_id: int) -> Optional[IntegrationStatus]:
        """Get integration status for a user."""
        from app.services.integration import IntegrationService
        integration_service = IntegrationService(self.db)
        return integration_service._get_user_integration_by_type(user_id, self.integration_slug)
    
    @abstractmethod
    def _cleanup_integration_data(self, integration_status: IntegrationStatus) -> None:
        """
        Clean up integration-specific data (tokens, configs).
        Should delete sensitive data but preserve IntegrationStatus for history.
        """
        pass
    
    def _validate_user(self, user: dict) -> int:
        user_id = user.get("user_id")
        if not user_id:
            raise AuthenticationError("Invalid user session")
        return user_id
    
    def _handle_error(self, operation: str, error: Exception) -> None:
        if isinstance(error, (NotFoundError, AuthenticationError, DatabaseError, BusinessLogicError)):
            raise error
        
        raise BusinessLogicError(
            f"Failed to {operation} for {self.integration_display_name}",
            details={"error": str(error)}
        )
