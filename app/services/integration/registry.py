"""
Integration Handler Registry

This module provides a registry pattern for managing integration handlers.
Makes it easy to add new integration types without modifying core logic.
"""

from typing import Dict, Type, Optional
from sqlalchemy.orm import Session

from app.services.integration.base_handler import BaseIntegrationHandler
from app.services.integration.handlers import (
    GmailIntegrationHandler,
    WhatsAppIntegrationHandler,
    DefaultIntegrationHandler
)


class IntegrationHandlerRegistry:
    """
    Registry for integration handlers using the Registry pattern.
    
    This class manages all integration handlers and provides a centralized
    way to retrieve the appropriate handler for each integration type.
    
    Design Pattern: Registry Pattern + Factory Pattern
    """
    
    _handlers: Dict[str, Type[BaseIntegrationHandler]] = {}
    _instances: Dict[str, BaseIntegrationHandler] = {}
    
    @classmethod
    def register(cls, integration_type: str, handler_class: Type[BaseIntegrationHandler]) -> None:
        """
        Register a new integration handler.
        
        Args:
            integration_type: The integration type identifier (e.g., 'gmail')
            handler_class: The handler class to register
        """
        cls._handlers[integration_type.lower()] = handler_class
    
    @classmethod
    def get_handler(cls, integration_type: str, db: Session) -> BaseIntegrationHandler:
        """
        Get the appropriate handler for an integration type.
        
        Args:
            integration_type: The integration type identifier
            db: Database session
            
        Returns:
            Integration handler instance
        """
        integration_type_lower = integration_type.lower()
        
        # Return cached instance if available
        cache_key = f"{integration_type_lower}_{id(db)}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # Get handler class or use default
        handler_class = cls._handlers.get(
            integration_type_lower,
            DefaultIntegrationHandler
        )
        
        # Create and cache instance
        if handler_class == DefaultIntegrationHandler:
            instance = handler_class(db, integration_type, integration_type.title())
        else:
            instance = handler_class(db)
        
        cls._instances[cache_key] = instance
        return instance
    
    @classmethod
    def is_registered(cls, integration_type: str) -> bool:
        """
        Check if a handler is registered for an integration type.
        
        Args:
            integration_type: The integration type identifier
            
        Returns:
            True if registered, False otherwise
        """
        return integration_type.lower() in cls._handlers
    
    @classmethod
    def get_registered_types(cls) -> list[str]:
        """
        Get list of all registered integration types.
        
        Returns:
            List of integration type identifiers
        """
        return list(cls._handlers.keys())
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear the handler instance cache."""
        cls._instances.clear()


# Register default handlers
IntegrationHandlerRegistry.register('gmail', GmailIntegrationHandler)
IntegrationHandlerRegistry.register('whatsapp', WhatsAppIntegrationHandler)


# Convenience function to add new integrations easily
def register_integration_handler(
    integration_type: str,
    handler_class: Type[BaseIntegrationHandler]
) -> None:
    """
    Convenience function to register a new integration handler.
    
    Usage:
        register_integration_handler('slack', SlackIntegrationHandler)
    
    Args:
        integration_type: The integration type identifier
        handler_class: The handler class to register
    """
    IntegrationHandlerRegistry.register(integration_type, handler_class)
