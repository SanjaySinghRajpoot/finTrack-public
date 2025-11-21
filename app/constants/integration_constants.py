"""
Integration-related constants for the application.
Contains static data for integration definitions, features, and messages.
"""

from typing import Dict, List
from enum import Enum


class IntegrationCategory(str, Enum):
    """Integration categories"""
    EMAIL = "email"
    MESSAGING = "messaging"
    STORAGE = "storage"
    PAYMENT = "payment"
    ACCOUNTING = "accounting"


class IntegrationProvider(str, Enum):
    """Integration providers"""
    GOOGLE = "Google"
    META = "Meta"
    MICROSOFT = "Microsoft"
    APPLE = "Apple"


class FeatureKey(str, Enum):
    """Feature keys for integrations"""
    # Email features
    EMAIL_PROCESSING = "email_processing"
    PDF_EXTRACTION = "pdf_extraction"
    DOCUMENT_CLASSIFICATION = "document_classification"
    EXPENSE_CATEGORIZATION = "expense_categorization"
    GMAIL_SYNC = "GMAIL_SYNC"
    GMAIL_SEND = "GMAIL_SEND"
    FILE_UPLOAD = "FILE_UPLOAD"
    
    # WhatsApp features
    WHATSAPP_SYNC = "WHATSAPP_SYNC"
    WHATSAPP_SEND = "WHATSAPP_SEND"


# Integration definitions with their features
INTEGRATION_DEFINITIONS: Dict[str, Dict] = {
    'gmail': {
        'name': 'Gmail',
        'description': 'Gmail email integration for processing financial documents and receipts',
        'provider': IntegrationProvider.GOOGLE.value,
        'category': IntegrationCategory.EMAIL.value,
        'icon_url': '/icons/gmail.svg',
        'features': [
            FeatureKey.EMAIL_PROCESSING.value,
            FeatureKey.PDF_EXTRACTION.value,
            FeatureKey.DOCUMENT_CLASSIFICATION.value,
            FeatureKey.EXPENSE_CATEGORIZATION.value
        ],
        'display_order': 1
    },
    'whatsapp': {
        'name': 'WhatsApp Business',
        'description': 'WhatsApp Business API integration for document processing',
        'provider': IntegrationProvider.META.value,
        'category': IntegrationCategory.MESSAGING.value,
        'icon_url': '/icons/whatsapp.svg',
        'features': [
            FeatureKey.PDF_EXTRACTION.value,
            FeatureKey.DOCUMENT_CLASSIFICATION.value
        ],
        'display_order': 2
    }
}


# Default integrations for initialization
DEFAULT_INTEGRATIONS: List[Dict] = [
    {
        "name": "Gmail",
        "slug": "gmail",
        "description": "Google Gmail integration for email processing and automation",
        "provider": IntegrationProvider.GOOGLE.value,
        "category": IntegrationCategory.EMAIL.value,
        "icon_url": "/icons/gmail.svg",
        "features": [
            {"feature_key": FeatureKey.GMAIL_SYNC.value, "execution_order": 1},
            {"feature_key": FeatureKey.GMAIL_SEND.value, "execution_order": 2},
            {"feature_key": FeatureKey.EMAIL_PROCESSING.value, "execution_order": 3}
        ]
    },
    {
        "name": "WhatsApp Business",
        "slug": "whatsapp",
        "description": "WhatsApp Business API integration for messaging automation",
        "provider": IntegrationProvider.META.value,
        "category": IntegrationCategory.MESSAGING.value,
        "icon_url": "/icons/whatsapp.svg",
        "features": [
            {"feature_key": FeatureKey.WHATSAPP_SYNC.value, "execution_order": 1},
            {"feature_key": FeatureKey.WHATSAPP_SEND.value, "execution_order": 2}
        ]
    }
]


# Status messages
class IntegrationMessages:
    """Integration-related messages"""
    INTEGRATION_NOT_FOUND = "Integration '{slug}' not found"
    FEATURE_NOT_AVAILABLE = "Feature '{feature}' not available for {integration}"
    INTEGRATION_CREATED = "Dynamically created integration: {name}"
    INTEGRATION_CREATION_FAILED = "Failed to create integration {slug}: {error}"
    NO_FEATURES_AVAILABLE = "No features available"
    AVAILABLE = "Available"
    INTEGRATION_CONFIG_NOT_FOUND = "Integration configuration not found"


# Default values
class IntegrationDefaults:
    """Default values for integrations"""
    DYNAMIC_DISPLAY_ORDER = 99
    DEFAULT_EXECUTION_ORDER = 1
    FALLBACK_CREDIT_COST = 1
