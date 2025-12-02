"""
Integration Validators

This module provides validation utilities for integrations.
Helps ensure data integrity and proper configuration.
"""

from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field, validator
from datetime import datetime


class IntegrationConfigValidator(BaseModel):
    """Base validator for integration configurations."""
    
    class Config:
        arbitrary_types_allowed = True


class EmailConfigValidator(IntegrationConfigValidator):
    """Validator for email integration configurations."""
    
    email_address: str = Field(..., min_length=3)
    provider: str
    verified: bool = False
    credentials: Optional[Dict[str, Any]] = None
    connected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    @validator('email_address')
    def validate_email(cls, v):
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email address format')
        return v
    
    @validator('credentials')
    def validate_credentials(cls, v):
        """Validate credentials structure."""
        if v is not None:
            required_keys = ['encrypted_access', 'encrypted_refresh']
            for key in required_keys:
                if key not in v:
                    raise ValueError(f'Missing required credential key: {key}')
        return v


class WhatsAppConfigValidator(IntegrationConfigValidator):
    """Validator for WhatsApp integration configurations."""
    
    phone_number: str = Field(..., min_length=10, max_length=15)
    verified: bool = False
    connected_at: Optional[datetime] = None
    business_account_id: Optional[str] = None
    
    @validator('phone_number')
    def validate_phone(cls, v):
        """Validate phone number format."""
        import re
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        # Check if it's a valid international format
        if not re.match(r'^\+?[1-9]\d{9,14}$', cleaned):
            raise ValueError('Invalid phone number format')
        return cleaned


class IntegrationValidator:
    """
    Validation service for integration data.
    
    Provides methods to validate integration configurations,
    features, and business rules.
    """
    
    @staticmethod
    def validate_integration_config(
        integration_type: str,
        config_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate integration configuration data.
        
        Args:
            integration_type: Type of integration
            config_data: Configuration data to validate
            
        Returns:
            Tuple of (is_valid, error_message, validated_data)
        """
        try:
            if integration_type.lower() in ['gmail', 'email']:
                validated = EmailConfigValidator(**config_data)
            elif integration_type.lower() == 'whatsapp':
                validated = WhatsAppConfigValidator(**config_data)
            else:
                # Generic validation
                return True, None, config_data
            
            return True, None, validated.dict()
            
        except Exception as e:
            return False, str(e), None
    
    @staticmethod
    def validate_feature_configuration(
        feature_key: str,
        custom_config: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate feature-specific configuration.
        
        Args:
            feature_key: The feature key
            custom_config: Custom configuration data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if custom_config is None:
            return True, None
        
        # Add feature-specific validation logic here
        # Example: validate email_processing config
        if feature_key == 'email_processing':
            required_keys = ['max_emails_per_sync', 'attachment_types']
            for key in required_keys:
                if key not in custom_config:
                    return False, f"Missing required config key: {key}"
        
        return True, None
    
    @staticmethod
    def validate_sync_interval(interval_minutes: int) -> Tuple[bool, Optional[str]]:
        """
        Validate sync interval settings.
        
        Args:
            interval_minutes: Sync interval in minutes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        MIN_INTERVAL = 5  # 5 minutes
        MAX_INTERVAL = 1440  # 24 hours
        
        if interval_minutes < MIN_INTERVAL:
            return False, f"Sync interval must be at least {MIN_INTERVAL} minutes"
        
        if interval_minutes > MAX_INTERVAL:
            return False, f"Sync interval cannot exceed {MAX_INTERVAL} minutes"
        
        return True, None
    
    @staticmethod
    def validate_integration_status_transition(
        current_status: str,
        new_status: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate status transition rules.
        
        Args:
            current_status: Current integration status
            new_status: Desired new status
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Define valid status transitions
        valid_transitions = {
            'pending': ['connected', 'error', 'disconnected'],
            'connected': ['syncing', 'error', 'disconnected'],
            'syncing': ['connected', 'error'],
            'error': ['connected', 'disconnected'],
            'disconnected': ['connected']
        }
        
        if current_status not in valid_transitions:
            return True, None  # Allow unknown statuses
        
        if new_status not in valid_transitions[current_status]:
            return False, f"Invalid status transition from {current_status} to {new_status}"
        
        return True, None
