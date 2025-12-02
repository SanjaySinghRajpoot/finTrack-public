"""Concrete Integration Handlers"""

from typing import Dict, Any, Optional
from datetime import datetime

from app.models.models import IntegrationStatus
from app.services.integration.base_handler import BaseIntegrationHandler


class GmailIntegrationHandler(BaseIntegrationHandler):
    
    @property
    def integration_type(self) -> str:
        return "gmail"
    
    @property
    def display_name(self) -> str:
        return "Gmail"
    
    def extract_config_details(self, user_integration: IntegrationStatus) -> Dict[str, Any]:
        if not user_integration.email_config:
            return {}
        
        email_config = user_integration.email_config
        
        return {
            "connected_email": email_config.email_address,
            "provider": email_config.provider,
            "verified": email_config.verified,
            "connected_at": email_config.connected_at,
            "expires_at": email_config.expires_at,
        }
    
    def validate_connection(self, user_integration: IntegrationStatus) -> tuple[bool, Optional[str]]:
        if not user_integration.email_config:
            return False, "Email configuration missing"
        
        if user_integration.email_config.expires_at:
            if user_integration.email_config.expires_at < datetime.utcnow():
                return False, "Authentication token expired"
        
        if not user_integration.email_config.credentials:
            return False, "Authentication credentials missing"
        
        return True, None
    
    def format_display_identifier(self, user_integration: IntegrationStatus) -> Optional[str]:
        if user_integration.email_config:
            return user_integration.email_config.email_address
        return None
    
    def get_required_fields(self) -> list[str]:
        return ["email_address", "credentials"]
    
    def get_health_status(self, user_integration: IntegrationStatus) -> Dict[str, Any]:
        issues = []
        
        if not user_integration.email_config:
            issues.append("Email configuration missing")
        elif user_integration.email_config.expires_at:
            time_until_expiry = user_integration.email_config.expires_at - datetime.utcnow()
            if time_until_expiry.days < 7:
                issues.append(f"Token expires in {time_until_expiry.days} days")
        
        return {
            "healthy": len(issues) == 0,
            "last_check": datetime.utcnow(),
            "issues": issues,
            "token_expires_at": user_integration.email_config.expires_at if user_integration.email_config else None
        }


class WhatsAppIntegrationHandler(BaseIntegrationHandler):
    
    @property
    def integration_type(self) -> str:
        return "whatsapp"
    
    @property
    def display_name(self) -> str:
        return "WhatsApp Business"
    
    def extract_config_details(self, user_integration: IntegrationStatus) -> Dict[str, Any]:
        if not user_integration.whatsapp_config:
            return {}
        
        whatsapp_config = user_integration.whatsapp_config
        
        return {
            "connected_number": whatsapp_config.phone_number,
            "verified": whatsapp_config.verified,
            "connected_at": whatsapp_config.connected_at,
        }
    
    def validate_connection(self, user_integration: IntegrationStatus) -> tuple[bool, Optional[str]]:
        if not user_integration.whatsapp_config:
            return False, "WhatsApp configuration missing"
        
        if not user_integration.whatsapp_config.verified:
            return False, "Phone number not verified"
        
        return True, None
    
    def format_display_identifier(self, user_integration: IntegrationStatus) -> Optional[str]:
        if user_integration.whatsapp_config:
            return user_integration.whatsapp_config.phone_number
        return None
    
    def get_required_fields(self) -> list[str]:
        return ["phone_number", "verified"]
    
    def get_health_status(self, user_integration: IntegrationStatus) -> Dict[str, Any]:
        issues = []
        
        if not user_integration.whatsapp_config:
            issues.append("WhatsApp configuration missing")
        elif not user_integration.whatsapp_config.verified:
            issues.append("Phone number not verified")
        
        return {
            "healthy": len(issues) == 0,
            "last_check": datetime.utcnow(),
            "issues": issues,
            "phone_number": user_integration.whatsapp_config.phone_number if user_integration.whatsapp_config else None
        }


class DefaultIntegrationHandler(BaseIntegrationHandler):
    """Fallback handler for unknown integration types."""
    
    def __init__(self, db, integration_type: str, display_name: str = None):
        super().__init__(db)
        self._integration_type = integration_type
        self._display_name = display_name or integration_type.title()
    
    @property
    def integration_type(self) -> str:
        return self._integration_type
    
    @property
    def display_name(self) -> str:
        return self._display_name
    
    def extract_config_details(self, user_integration: IntegrationStatus) -> Dict[str, Any]:
        return {
            "integration_type": self.integration_type,
            "status": user_integration.status.value if user_integration.status else "unknown"
        }
