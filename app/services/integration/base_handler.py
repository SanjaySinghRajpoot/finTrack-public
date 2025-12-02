"""
Base Integration Handler

Abstract base class for all integration handlers.
Implements Strategy + Template Method patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.models import IntegrationStatus


class BaseIntegrationHandler(ABC):
    
    def __init__(self, db: Session):
        self._db = db
    
    @property
    def db(self) -> Session:
        return self._db
    
    @property
    @abstractmethod
    def integration_type(self) -> str:
        """Return integration type (e.g., 'gmail', 'whatsapp')"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return human-readable name"""
        pass
    
    @abstractmethod
    def extract_config_details(self, user_integration: IntegrationStatus) -> Dict[str, Any]:
        """
        Extract integration-specific configuration details.
        Returns dict to be added to integration detail schema.
        """
        pass
    
    def validate_connection(self, user_integration: IntegrationStatus) -> tuple[bool, Optional[str]]:
        """Validate integration connection. Override for custom logic."""
        return True, None
    
    def on_create(self, user_integration: IntegrationStatus, **kwargs) -> None:
        """Hook called when integration is first created."""
        pass
    
    def on_connect(self, user_integration: IntegrationStatus, **kwargs) -> None:
        """Hook called when integration is connected/authenticated."""
        pass
    
    def on_disconnect(self, user_integration: IntegrationStatus) -> None:
        """Hook called when integration is disconnected."""
        pass
    
    def on_sync_start(self, user_integration: IntegrationStatus) -> None:
        """Hook called before sync operation starts."""
        pass
    
    def on_sync_complete(self, user_integration: IntegrationStatus, result: Dict[str, Any]) -> None:
        """Hook called after sync operation completes."""
        pass
    
    def get_health_status(self, user_integration: IntegrationStatus) -> Dict[str, Any]:
        """Get health status of the integration."""
        return {
            "healthy": True,
            "last_check": None,
            "issues": []
        }
    
    def get_required_fields(self) -> List[str]:
        """Get list of required configuration fields."""
        return []
    
    def format_display_identifier(self, user_integration: IntegrationStatus) -> Optional[str]:
        """Format user-friendly identifier (email, phone, etc.)"""
        return None
