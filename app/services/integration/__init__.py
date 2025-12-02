"""
Integration Module

This module provides services for managing integrations and their features.
The module is organized into specialized sub-services following the Single
Responsibility Principle and Facade design pattern.

Main Components:
- IntegrationService: Main facade for all integration operations
- IntegrationQueryService: Handles database queries
- IntegrationCreationService: Handles integration creation
- BaseIntegrationHandler: Abstract base for integration-specific handlers
- IntegrationHandlerRegistry: Registry for managing handlers

Note: FeatureService has been moved to app.services.feature_service for better organization.

Usage:
    from app.services.integration import IntegrationService
    from app.services.feature_service import FeatureService
    
    # Initialize with database session
    integration_service = IntegrationService(db)
    feature_service = FeatureService(db)
    
    # Use the service
    integrations = integration_service.get_all_integrations()
"""

from app.services.integration.service import IntegrationService
from app.services.integration.query_service import IntegrationQueryService
from app.services.integration.creation_service import IntegrationCreationService
from app.services.integration.base_handler import BaseIntegrationHandler
from app.services.integration.registry import IntegrationHandlerRegistry, register_integration_handler
from app.services.integration.validators import IntegrationValidator

__all__ = [
    'IntegrationService',
    'IntegrationQueryService',
    'IntegrationCreationService',
    'BaseIntegrationHandler',
    'IntegrationHandlerRegistry',
    'register_integration_handler',
    'IntegrationValidator'
]
