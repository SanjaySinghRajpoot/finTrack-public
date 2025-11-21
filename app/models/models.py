import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Column, Integer, String, Float, Date, Enum, Text, ForeignKey, Boolean,
    DateTime, JSON, func, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
import json
import enum
from sqlalchemy.orm import Session
from sqlalchemy.event import listens_for

# ================================================================================================
# BASE CLASSES AND MIXINS
# ================================================================================================

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass

class TimestampMixin:
    """Mixin class for common timestamp fields"""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SoftDeleteMixin:
    """Mixin class for soft delete functionality"""
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

# ================================================================================================
# ENUMS
# ================================================================================================

class SourceType(str, enum.Enum):
    """Source types for tracking data origins"""
    email = "email"
    whatsapp = "whatsapp"
    gdrive = "gdrive"
    manual = "manual"

class DocumentType(enum.Enum):
    """Document types for processed email data"""
    INVOICE = "invoice"
    BILL = "bill"
    EMI = "emi"
    PAYMENT_RECEIPT = "payment_receipt"
    TAX_INVOICE = "tax_invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    OTHER = "other"

class IntegrationType(str, enum.Enum):
    """Available integration types"""
    gmail = "gmail"
    whatsapp = "whatsapp"

class IntegrationState(str, enum.Enum):
    """Integration connection states"""
    connected = "connected"
    disconnected = "disconnected"
    error = "error"
    pending = "pending"

class SubscriptionStatus(str, enum.Enum):
    """Subscription status options"""
    trial = "trial"
    active = "active"
    expired = "expired"
    cancelled = "cancelled"

# ================================================================================================
# USER MANAGEMENT MODELS
# ================================================================================================

class User(Base, TimestampMixin):
    """User model for authentication and profile management"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Google profile details
    email = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    
    # Authentication
    password = Column(String, nullable=True)
    
    # Localization
    locale = Column(String, nullable=True)
    country = Column(String, nullable=True)
    
    # Relationships
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    processed_data = relationship("ProcessedEmailData", back_populates="user", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    integration_status = relationship("IntegrationStatus", back_populates="user", cascade="all, delete-orphan")
    manual_uploads = relationship("ManualUpload", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

class UserToken(Base, TimestampMixin):
    """OAuth tokens for user authentication"""
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False, default="google")
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<UserToken(id={self.id}, user_id={self.user_id}, provider={self.provider})>"

# ================================================================================================
# SOURCE TRACKING MODELS
# ================================================================================================

class Source(Base):
    """Source tracking table for data origins"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False, index=True)

    # Can we keep this an Int?
    external_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    emails = relationship("Email", back_populates="source", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="source", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="source")
    processed_data = relationship("ProcessedEmailData", back_populates="source")

    __table_args__ = (
        UniqueConstraint("type", "external_id", name="uq_source_type_external_id"),
        Index("ix_source_type_external_id", "type", "external_id"),
        Index("ix_source_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Source(id={self.id}, type={self.type}, external_id={self.external_id})>"

# ================================================================================================
# EMAIL PROCESSING MODELS
# ================================================================================================

class Email(Base, TimestampMixin):
    """Email data from Gmail API"""
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # User reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Source reference
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=True, index=True)

    # Gmail specific identifiers
    gmail_message_id = Column(String(255), unique=True, nullable=False)
    gmail_thread_id = Column(String(255), nullable=True)

    # Email details
    from_address = Column(String(512), nullable=True)
    to_address = Column(Text, nullable=True)
    cc_address = Column(Text, nullable=True)
    bcc_address = Column(Text, nullable=True)
    
    subject = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    plain_text_content = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)

    # System info
    type = Column(String(100), nullable=True)
    is_read = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    labels = Column(JSON, nullable=True)

    # Metadata
    meta_data = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User")
    source = relationship("Source")
    attachments = relationship(
        "Attachment",
        primaryjoin="Email.source_id == foreign(Attachment.source_id)",
        viewonly=True
    )
    processed_data = relationship("ProcessedEmailData", back_populates="email", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Email(id={self.id}, gmail_message_id={self.gmail_message_id})>"

class Attachment(Base):
    """Attachments with source references"""
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    attachment_id = Column(String(1000), unique=True, nullable=False)

    # File details
    filename = Column(String(512), nullable=False)
    mime_type = Column(String(255), nullable=True)
    size = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash for duplicate detection

    # Storage references
    storage_path = Column(String(1024), nullable=True)
    s3_url = Column(String(512), nullable=True)
    extracted_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source = relationship("Source", back_populates="attachments")
    # Relationship to ProcessedEmailData through source_id
    processed_email_data = relationship(
        "ProcessedEmailData",
        primaryjoin="Attachment.source_id == foreign(ProcessedEmailData.source_id)",
        viewonly=True,
        uselist=False  # One attachment typically corresponds to one processed email data
    )
    # manual_uploads = relationship("ManualUpload", back_populates="attachment", cascade="all, delete-orphan")
    # Keep email relationship for backward compatibility during migration
    # email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=True)
    # email = relationship("Email", back_populates="attachments")

    def __repr__(self):
        return f"<Attachment(id={self.id}, filename={self.filename})>"

class ManualUpload(Base, TimestampMixin):
    """Manual upload records to track user-uploaded files"""
    __tablename__ = "manual_uploads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)

    # References
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Upload metadata only (file details are in attachments table)
    document_type = Column(Enum(DocumentType), nullable=False, default=DocumentType.INVOICE)
    upload_method = Column(String(50), default="web_upload")  # web_upload, mobile_app, api
    upload_notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index("idx_manual_uploads_user_created", "user_id", "created_at"),
    )

class ProcessedEmailData(Base, TimestampMixin):
    """Processed and structured data extracted from emails"""
    __tablename__ = "processed_email_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # References
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    # Keep email_id for backward compatibility during migration
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=True)

    # Document details
    document_type = Column(String, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    document_number = Column(String(100), nullable=True)
    reference_id = Column(String(100), nullable=True)

    # Dates
    issue_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)

    # Financial details
    amount = Column(Float, nullable=True)
    currency = Column(String(10), default="INR")
    is_paid = Column(Boolean, default=False)
    payment_method = Column(String(50), nullable=True)

    # Vendor information
    vendor_name = Column(String(255), nullable=True)
    vendor_gstin = Column(String(50), nullable=True)

    # Classification
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)

    # Storage and metadata
    file_url = Column(String(500), nullable=True)
    meta_data = Column(JSON, nullable=True)
    is_imported = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="processed_data")
    source = relationship("Source", back_populates="processed_data")
    email = relationship("Email", back_populates="processed_data")

    # Relationship to Attachment through source_id
    attachment = relationship(
        "Attachment",
        primaryjoin="ProcessedEmailData.source_id == foreign(Attachment.source_id)",
        viewonly=True,
        uselist=False  # One processed email data typically has one attachment
    )

    # Link to expenses through source_id for proper data lineage
    expenses = relationship(
        "Expense",
        primaryjoin="ProcessedEmailData.source_id == foreign(Expense.source_id)",
        viewonly=True
    )

    processed_items = relationship(
        "ProcessedItem",
        backref="processed_email_data",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ProcessedEmailData(id={self.id}, document_type={self.document_type})>"

class ProcessedItem(Base, TimestampMixin):
    """
    Stores individual item details extracted from processed invoices/emails.
    Each item corresponds to a line in an invoice, linked to ProcessedEmailData.
    """
    __tablename__ = "processed_items"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Reference to the parent processed invoice
    processed_email_id = Column(
        Integer,
        ForeignKey("processed_email_data.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key linking to processed_email_data (invoice-level record)"
    )

    # Item details
    item_name = Column(String(255), nullable=False, comment="Name/description of the product or service")
    item_code = Column(String(100), nullable=True, comment="Optional product/service code or SKU")
    category = Column(String(100), nullable=True, comment="Product or service category (if available)")

    # Quantitative details
    quantity = Column(Float, nullable=False, default=1.0, comment="Quantity of the product/service")
    unit = Column(String(50), nullable=True, comment="Unit of measurement, e.g., pcs, kg, hr")

    # Pricing details
    rate = Column(Float, nullable=False, comment="Rate per unit of the item")
    discount = Column(Float, nullable=True, default=0.0, comment="Discount applied on the item, if any")
    tax_percent = Column(Float, nullable=True, comment="Applicable tax percentage")
    total_amount = Column(Float, nullable=True, comment="Total amount for the item (after discount, before tax)")

    # Metadata
    currency = Column(String(10), default="INR", nullable=False)
    meta_data = Column(JSON, nullable=True, comment="Raw extracted or extra data (for auditing or debugging)")

    # Relationship
    # processed_email = relationship(
    #     "ProcessedEmailData",
    #     back_populates="items",
    #     lazy="joined"
    # )

    def __repr__(self):
        return f"<ProcessedEmailItem(id={self.id}, item_name={self.item_name}, amount={self.total_amount})>"

# ================================================================================================
# EXPENSE MANAGEMENT MODELS
# ================================================================================================

class Expense(Base, TimestampMixin, SoftDeleteMixin):
    """User expense records"""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)

    # References
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True)

    # Expense details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    category = Column(String(50), index=True, nullable=False)
    description = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="expenses")
    source = relationship("Source", back_populates="expenses")

    # Link to ProcessedEmailData through source_id for proper data lineage
    processed_data = relationship(
        "ProcessedEmailData",
        primaryjoin="Expense.source_id == foreign(ProcessedEmailData.source_id)",
        viewonly=True
    )

    def __repr__(self):
        return f"<Expense(id={self.id}, amount={self.amount}, category={self.category})>"

# Indexes for optimization
Index("idx_expenses_user_category", Expense.user_id, Expense.category)
Index("idx_expenses_user_created", Expense.user_id, Expense.created_at)

# ================================================================================================
# INTEGRATION MANAGEMENT MODELS
# ================================================================================================

class Integration(Base, TimestampMixin):
    """Master table for available integrations"""
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    provider = Column(String(100), nullable=True)
    
    # Metadata
    icon_url = Column(String(500), nullable=True)
    documentation_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    category = Column(String(50), nullable=True)

    # Relationships
    integration_features = relationship("IntegrationFeature", back_populates="integration", cascade="all, delete-orphan")
    user_integrations = relationship("IntegrationStatus", back_populates="integration")

    def __repr__(self):
        return f"<Integration(id={self.id}, name={self.name})>"

class IntegrationStatus(Base):
    """User-specific integration status and sync tracking"""
    __tablename__ = "integration_status"

    id = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    integration_master_id = Column(Integer, ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    integration_type = Column(Enum(IntegrationType), nullable=False)

    # Status details
    status = Column(Enum(IntegrationState), default=IntegrationState.pending)
    error_message = Column(String, nullable=True)

    # Sync tracking
    last_synced_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)
    sync_interval_minutes = Column(Integer, default=60)
    last_sync_duration = Column(Integer, nullable=True)
    total_syncs = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_checked = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="integration_status")
    integration = relationship("Integration", back_populates="user_integrations")
    email_config = relationship("EmailConfig", back_populates="integration_status", uselist=False)
    whatsapp_config = relationship("WhatsappConfig", back_populates="integration_status", uselist=False)

    __table_args__ = (
        UniqueConstraint("user_id", "integration_type", name="unique_user_integration"),
    )

    def __repr__(self):
        return f"<IntegrationStatus(user_id={self.user_id}, type={self.integration_type}, status={self.status})>"

class EmailConfig(Base, TimestampMixin):
    """Gmail integration configuration"""
    __tablename__ = "email_config"

    id = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    integration_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("integration_status.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    
    # Email details
    email_address = Column(String, nullable=False)
    provider = Column(String, default="gmail")
    credentials = Column(JSON, nullable=False)
    verified = Column(Boolean, default=False)
    connected_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    integration_status = relationship("IntegrationStatus", back_populates="email_config")

    def __repr__(self):
        return f"<EmailConfig(email={self.email_address}, verified={self.verified})>"

class WhatsappConfig(Base, TimestampMixin):
    """WhatsApp integration configuration"""
    __tablename__ = "whatsapp_config"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("integration_status.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    
    # WhatsApp details
    phone_number = Column(String, nullable=False)
    business_id = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    connected_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    integration_status = relationship("IntegrationStatus", back_populates="whatsapp_config")

    def __repr__(self):
        return f"<WhatsappConfig(phone={self.phone_number}, verified={self.verified})>"

# ================================================================================================
# SUBSCRIPTION AND BILLING MODELS
# ================================================================================================

class Plan(Base, TimestampMixin):
    """Subscription plans with credit allocation"""
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    
    # Pricing
    price = Column(Float, nullable=False, default=0.0)
    currency = Column(String(3), default="INR")
    billing_cycle = Column(String(20), nullable=False)

    # Credits
    total_credits = Column(Integer, nullable=False, default=0)
    credit_rollover_limit = Column(Integer, nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    # Relationships
    plan_features = relationship("PlanFeature", back_populates="plan", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="plan")

    def __repr__(self):
        return f"<Plan(id={self.id}, name={self.name}, credits={self.total_credits})>"

class Feature(Base):
    """System features that consume credits"""
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_key = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    credit_cost = Column(Integer, nullable=False, default=1)
    category = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    plan_features = relationship("PlanFeature", back_populates="feature")
    credit_history = relationship("CreditHistory", back_populates="feature")
    integration_features = relationship("IntegrationFeature", back_populates="feature")

    def __repr__(self):
        return f"<Feature(key={self.feature_key}, cost={self.credit_cost})>"

class PlanFeature(Base):
    """Junction table for plan-feature relationships"""
    __tablename__ = "plan_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), nullable=False)
    is_enabled = Column(Boolean, default=True)
    custom_credit_cost = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    plan = relationship("Plan", back_populates="plan_features")
    feature = relationship("Feature", back_populates="plan_features")

    __table_args__ = (
        UniqueConstraint("plan_id", "feature_id", name="unique_plan_feature"),
    )

class Subscription(Base, TimestampMixin):
    """User subscription with credit tracking"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)

    # Status and duration
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.trial)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Credits
    credit_balance = Column(Integer, nullable=False, default=0)
    total_credits_allocated = Column(Integer, nullable=False, default=0)
    
    # Settings
    auto_renewal = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    credit_history = relationship("CreditHistory", back_populates="subscription", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, plan={self.plan.name if self.plan else 'N/A'}, credits={self.credit_balance})>"

class CreditHistory(Base):
    """Credit usage transaction log"""
    __tablename__ = "credit_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    feature_id = Column(Integer, ForeignKey("features.id", ondelete="SET NULL"), nullable=True)

    # Transaction details
    credits_before = Column(Integer, nullable=False)
    credits_used = Column(Integer, nullable=False, default=0)
    credits_after = Column(Integer, nullable=False)
    action_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subscription = relationship("Subscription", back_populates="credit_history")
    feature = relationship("Feature", back_populates="credit_history")

    def __repr__(self):
        return f"<CreditHistory(id={self.id}, action={self.action_type}, credits_used={self.credits_used})>"

class IntegrationFeature(Base, TimestampMixin):
    """Junction table for integration-feature relationships"""
    __tablename__ = "integration_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    integration_id = Column(Integer, ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    feature_id = Column(Integer, ForeignKey("features.id", ondelete="CASCADE"), nullable=False)
    
    # Configuration
    is_enabled = Column(Boolean, default=True)
    execution_order = Column(Integer, nullable=True)
    custom_config = Column(JSON, nullable=True)
    custom_credit_cost = Column(Integer, nullable=True)
    custom_display_name = Column(String(200), nullable=True)

    # Relationships
    integration = relationship("Integration", back_populates="integration_features")
    feature = relationship("Feature", back_populates="integration_features")

    __table_args__ = (
        UniqueConstraint("integration_id", "feature_id", name="unique_integration_feature"),
    )
