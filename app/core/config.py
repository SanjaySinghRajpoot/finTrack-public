"""
Centralized Configuration Management for FinTrack

This module provides a single source of truth for all application configuration.
Environment variables are loaded from:
1. System environment variables (including Docker Compose)
2. .env file in the project root

No default values - missing required values will raise an error.

Usage:
    from app.core.config import settings
    
    database_url = settings.DATABASE_URL
    jwt_secret = settings.JWT_SECRET
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All required fields must be set - no defaults provided.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # ==========================================================================
    # Application Settings
    # ==========================================================================
    HOST_URL: str
    FRONTEND_URL: str
    
    # ==========================================================================
    # Database Configuration
    # ==========================================================================
    DATABASE_URL: str
    
    # ==========================================================================
    # JWT Configuration
    # ==========================================================================
    JWT_SECRET: str
    JWT_ALGORITHM: str
    JWT_EXPIRY_MINUTES: int
    
    # ==========================================================================
    # Google OAuth Configuration
    # ==========================================================================
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    
    # ==========================================================================
    # AWS S3 Configuration
    # ==========================================================================
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET: str
    
    # ==========================================================================
    # OpenAI / LLM Configuration
    # ==========================================================================
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    LLM_MODEL: str
    
    # ==========================================================================
    # OCR Service Configuration
    # ==========================================================================
    DOCSTRANGE_API_KEY: str
    
    # ==========================================================================
    # Encryption Configuration
    # ==========================================================================
    ENCRYPTION_KEY: str
    
    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @property
    def OAUTH_REDIRECT_URI(self) -> str:
        """OAuth2 callback URL for login"""
        return f"{self.HOST_URL}/api/emails/oauth2callback"
    
    @property
    def GMAIL_INTEGRATION_REDIRECT_URI(self) -> str:
        """OAuth2 callback URL for Gmail integration"""
        return f"{self.HOST_URL}/api/integration/gmail/callback"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Global settings instance for easy import
settings = get_settings()


# ==========================================================================
# Convenience exports for backward compatibility
# ==========================================================================
DATABASE_URL = settings.DATABASE_URL
JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_EXPIRY_MINUTES = settings.JWT_EXPIRY_MINUTES
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
HOST_URL = settings.HOST_URL
FRONTEND_URL = settings.FRONTEND_URL
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
AWS_REGION = settings.AWS_REGION
AWS_S3_BUCKET = settings.AWS_S3_BUCKET
OPENAI_API_KEY = settings.OPENAI_API_KEY
ENCRYPTION_KEY = settings.ENCRYPTION_KEY
