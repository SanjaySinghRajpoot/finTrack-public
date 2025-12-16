"""
Centralized Configuration Management for FinTrack

This module provides a single source of truth for all application configuration.
It uses Pydantic Settings for type-safe environment variable management with validation.

Usage:
    from app.core.config import settings
    
    # Access any configuration
    database_url = settings.DATABASE_URL
    jwt_secret = settings.JWT_SECRET
"""

from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden by environment variables.
    Default values are provided where appropriate for development.
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
    APP_NAME: str = Field(default="FinTrack", description="Application name")
    APP_ENV: str = Field(default="development", description="Application environment (development, staging, production)")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    HOST_URL: str = Field(default="http://localhost:8000", description="Base URL of the application")
    FRONTEND_URL: str = Field(default="http://localhost:8080", description="Frontend application URL")
    
    # ==========================================================================
    # Database Configuration
    # ==========================================================================
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/fintrack",
        description="PostgreSQL database connection URL"
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Maximum overflow connections")
    
    # ==========================================================================
    # JWT Configuration
    # ==========================================================================
    JWT_SECRET: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token signing"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_EXPIRY_MINUTES: int = Field(default=1440, description="JWT token expiry in minutes (default: 24 hours)")
    
    # ==========================================================================
    # Google OAuth Configuration
    # ==========================================================================
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, description="Google OAuth2 Client ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, description="Google OAuth2 Client Secret")
    
    # ==========================================================================
    # AWS S3 Configuration
    # ==========================================================================
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS Access Key ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS Secret Access Key")
    AWS_REGION: str = Field(default="ap-south-1", description="AWS Region")
    AWS_S3_BUCKET: Optional[str] = Field(default=None, description="S3 Bucket name for file storage")
    
    # ==========================================================================
    # OpenAI / LLM Configuration
    # ==========================================================================
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API Key for LLM services")
    OPENAI_BASE_URL: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        description="OpenAI API base URL (can be changed for different providers)"
    )
    
    # ==========================================================================
    # OCR Service Configuration
    # ==========================================================================
    NANONETS_API_KEY: Optional[str] = Field(default=None, description="NanoNets API Key for OCR")
    DOCSTRANGE_API_KEY: Optional[str] = Field(default=None, description="DocStrange API Key (fallback OCR)")
    
    # ==========================================================================
    # Encryption Configuration
    # ==========================================================================
    ENCRYPTION_KEY: str = Field(
        default="X1Tz1y9Ff0QZxQ9fDd0tKXk8h1u4z6pF8H2xG4XK9sY=",
        description="Fernet encryption key for sensitive data"
    )
    
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
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.APP_ENV.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.APP_ENV.lower() == "development"
    
    # ==========================================================================
    # Validators
    # ==========================================================================
    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if v == "your-secret-key-change-in-production":
            import warnings
            warnings.warn(
                "Using default JWT_SECRET. Please set a secure JWT_SECRET in production!",
                UserWarning
            )
        return v
    
    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed = ["development", "staging", "production", "testing"]
        if v.lower() not in allowed:
            raise ValueError(f"APP_ENV must be one of: {allowed}")
        return v.lower()


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    Call get_settings.cache_clear() to reload settings if needed.
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
