"""
Pydantic schemas for integration-related data models.
Used for request/response validation and serialization.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class FeatureSchema(BaseModel):
    """Schema for feature information"""
    feature_id: int
    feature_key: str
    display_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    credit_cost: int
    execution_order: Optional[int] = None
    custom_config: Optional[Dict[str, Any]] = None
    is_enabled: bool = True

    model_config = ConfigDict(from_attributes=True)


class FeatureAvailabilitySchema(BaseModel):
    """Schema for feature availability information"""
    feature_key: str
    display_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    credit_cost: int
    can_use: bool
    usage_reason: str
    execution_order: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class IntegrationBasicSchema(BaseModel):
    """Basic integration information schema"""
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    provider: Optional[str] = None
    category: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

    model_config = ConfigDict(from_attributes=True)


class IntegrationWithFeaturesSchema(IntegrationBasicSchema):
    """Integration schema with features"""
    features: List[FeatureSchema] = []


class EmailConfigSchema(BaseModel):
    """Schema for email configuration"""
    connected_email: str
    provider: str
    verified: bool
    connected_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WhatsAppConfigSchema(BaseModel):
    """Schema for WhatsApp configuration"""
    connected_number: str
    verified: bool
    connected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserIntegrationDetailSchema(BaseModel):
    """Detailed schema for user's integration status"""
    integration_id: str
    integration_type: str
    status: str
    error_message: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None
    sync_interval_minutes: Optional[int] = None
    last_sync_duration: Optional[int] = None
    total_syncs: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Master integration details
    integration_name: Optional[str] = None
    integration_slug: Optional[str] = None
    provider: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    
    # Integration-specific config
    connected_email: Optional[str] = None
    connected_number: Optional[str] = None
    verified: Optional[bool] = None
    connected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Feature availability
    features: List[FeatureAvailabilitySchema] = []
    can_use_integration: bool = False
    usage_reason: str = "Unknown"
    primary_feature: Optional[FeatureAvailabilitySchema] = None

    model_config = ConfigDict(from_attributes=True)


class IntegrationFeatureAccessResult(BaseModel):
    """Result of checking integration feature access"""
    can_use: bool
    message: str
    details: Dict[str, Any]


class IntegrationCreationRequest(BaseModel):
    """Request schema for creating a new integration"""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    provider: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    icon_url: Optional[str] = Field(None, max_length=500)
    is_active: bool = True
    display_order: int = 0


class IntegrationFeatureConfig(BaseModel):
    """Configuration for an integration feature"""
    feature_key: str
    execution_order: Optional[int] = None
    custom_credit_cost: Optional[int] = None
    custom_display_name: Optional[str] = None
    is_enabled: bool = True


class IntegrationDefinition(BaseModel):
    """Complete integration definition with features"""
    name: str
    slug: str
    description: str
    provider: str
    category: str
    icon_url: Optional[str] = None
    features: List[str]
    display_order: int = 0

    model_config = ConfigDict(from_attributes=True)


# ================================================================================================
# SUBSCRIPTION SCHEMAS
# ================================================================================================

class SubscriptionDetailSchema(BaseModel):
    """Schema for subscription details"""
    has_subscription: bool
    credit_balance: int
    plan_name: Optional[str] = None
    plan_slug: Optional[str] = None
    subscription_status: Optional[str] = None
    expires_at: Optional[datetime] = None
    auto_renewal: bool = False

    model_config = ConfigDict(from_attributes=True)


class CreditValidationSchema(BaseModel):
    """Schema for credit validation results"""
    valid: bool
    error_code: Optional[str] = None
    message: str
    current_credits: int
    required_credits: int

    model_config = ConfigDict(from_attributes=True)


class CreditDeductionSchema(BaseModel):
    """Schema for credit deduction results"""
    success: bool
    message: str
    error: Optional[str] = None
    error_code: Optional[str] = None
    credits_deducted: int
    remaining_credits: int

    model_config = ConfigDict(from_attributes=True)


class FeatureAvailabilityDetailSchema(BaseModel):
    """Schema for feature availability with details"""
    display_name: str
    description: str
    credit_cost: int
    can_use: bool
    category: str
    reason: str

    model_config = ConfigDict(from_attributes=True)


class AllFeaturesAvailabilitySchema(BaseModel):
    """Schema for all features availability"""
    features: Dict[str, FeatureAvailabilityDetailSchema]

    model_config = ConfigDict(from_attributes=True)


class FeatureAccessDetailSchema(BaseModel):
    """Schema for specific feature access details"""
    feature_key: str
    display_name: str
    description: str
    credit_cost: int
    category: str
    current_balance: int

    model_config = ConfigDict(from_attributes=True)


class FeatureAccessCheckSchema(BaseModel):
    """Schema for feature access check results"""
    can_use: bool
    message: str
    feature_details: Optional[FeatureAccessDetailSchema] = None

    model_config = ConfigDict(from_attributes=True)


class CreditSummarySchema(BaseModel):
    """Schema for credit usage summary"""
    current_balance: int
    total_allocated: int
    credits_used: int
    usage_percentage: float

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreationSchema(BaseModel):
    """Schema for newly created subscription"""
    subscription_id: int
    user_id: int
    plan_id: int
    plan_name: str
    status: str
    starts_at: datetime
    expires_at: datetime
    credit_balance: int
    total_credits_allocated: int
    auto_renewal: bool

    model_config = ConfigDict(from_attributes=True)


class SubscriptionUpdateSchema(BaseModel):
    """Schema for subscription status update"""
    subscription_id: int
    status: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
