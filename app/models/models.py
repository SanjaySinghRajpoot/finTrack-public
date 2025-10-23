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

class Base(DeclarativeBase):
    pass 

class DocumentType(enum.Enum):
    INVOICE = "invoice"
    BILL = "bill"
    EMI = "emi"
    PAYMENT_RECEIPT = "payment_receipt"
    TAX_INVOICE = "tax_invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    OTHER = "other"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Google profile details
    email = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)  # URL to Google profile picture
    
    password = Column(String, nullable=True)  # store hashed password, not plain text
    locale = Column(String, nullable=True)      # e.g. "en", "hi"
    country = Column(String, nullable=True) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # reference to app user (who owns this email in your system)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Gmail specific identifiers
    gmail_message_id = Column(String(255), unique=True, nullable=False)
    gmail_thread_id = Column(String(255), nullable=True)

    # email details
    from_address = Column(String(512), nullable=True)
    to_address = Column(Text, nullable=True)         # store multiple recipients (comma separated or JSON)
    cc_address = Column(Text, nullable=True)
    bcc_address = Column(Text, nullable=True)
    
    subject = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)            # Gmail API returns a short snippet
    plain_text_content = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)

    # system info
    type = Column(String(100), nullable=True)        # e.g. "inbox", "sent", "draft"
    is_read = Column(Boolean, default=False)
    labels = Column(JSON, nullable=True)             # Gmail labels, store as JSON

    # additional metadata
    meta_data = Column(JSON, nullable=True)           # raw Gmail payload metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    attachments = relationship("Attachment", back_populates="email")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    attachment_id = Column(String(1000), unique=True, nullable=False)

    filename = Column(String(512), nullable=False)
    mime_type = Column(String(255), nullable=True)
    size = Column(Integer, nullable=True)

    # storage references
    storage_path = Column(String(1024), nullable=True)  # S3/GCS/Local path
    extracted_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    email = relationship("Email", back_populates="attachments")


class Base(DeclarativeBase):
    pass 

class DocumentType(enum.Enum):
    INVOICE = "invoice"
    BILL = "bill"
    EMI = "emi"
    PAYMENT_RECEIPT = "payment_receipt"
    TAX_INVOICE = "tax_invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    OTHER = "other"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Google profile details
    email = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)  # URL to Google profile picture
    
    password = Column(String, nullable=True)  # store hashed password, not plain text
    locale = Column(String, nullable=True)      # e.g. "en", "hi"
    country = Column(String, nullable=True) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # reference to app user (who owns this email in your system)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Gmail specific identifiers
    gmail_message_id = Column(String(255), unique=True, nullable=False)
    gmail_thread_id = Column(String(255), nullable=True)

    # email details
    from_address = Column(String(512), nullable=True)
    to_address = Column(Text, nullable=True)         # store multiple recipients (comma separated or JSON)
    cc_address = Column(Text, nullable=True)
    bcc_address = Column(Text, nullable=True)
    
    subject = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)            # Gmail API returns a short snippet
    plain_text_content = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)

    # system info
    type = Column(String(100), nullable=True)        # e.g. "inbox", "sent", "draft"
    is_read = Column(Boolean, default=False)
    labels = Column(JSON, nullable=True)             # Gmail labels, store as JSON

    # additional metadata
    meta_data = Column(JSON, nullable=True)           # raw Gmail payload metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    attachments = relationship("Attachment", back_populates="email")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    attachment_id = Column(String(1000), unique=True, nullable=False)

    filename = Column(String(512), nullable=False)
    mime_type = Column(String(255), nullable=True)
    size = Column(Integer, nullable=True)

    s3_url = Column(String(512), nullable=True)

    # storage references
    storage_path = Column(String(1024), nullable=True)  # S3/GCS/Local path
    extracted_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    email = relationship("Email", back_populates="attachments")


class ProcessedEmailData(Base):
    __tablename__ = "processed_email_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # link to user (redundant but useful for quick queries)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # link back to the source email
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)

    document_type = Column(String, nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    document_number = Column(String(100), nullable=True)
    reference_id = Column(String(100), nullable=True)

    issue_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)

    amount = Column(Float, nullable=True)
    currency = Column(String(10), default="INR")

    is_paid = Column(Boolean, default=False)
    payment_method = Column(String(50), nullable=True)

    vendor_name = Column(String(255), nullable=True)
    vendor_gstin = Column(String(50), nullable=True)

    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)

    file_url = Column(String(500), nullable=True)
    meta_data = Column(JSON, nullable=True)

    # if this is true that means the user has imported the Expense into the calculations
    is_imported = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False, default="google")
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserToken(id={self.id}, user_id={self.user_id}, provider={self.provider})>"

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    processed_email_id = Column(Integer, ForeignKey("processed_email_data.id", ondelete="SET NULL"), nullable=True, index=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    category = Column(String(50), index=True, nullable=False)
    description = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete

    user = relationship("User", back_populates="expenses")

# Extra indexes for optimization
Index("idx_expenses_user_category", Expense.user_id, Expense.category)
Index("idx_expenses_user_id", Expense.user_id)

# ---- Enum for Integration Type ----
class IntegrationType(str, enum.Enum):
    gmail = "gmail"
    whatsapp = "whatsapp"


# ---- Enum for Connection Status ----
class IntegrationState(str, enum.Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"
    pending = "pending"


# ---- IntegrationStatus Table ----
class IntegrationStatus(Base):
    __tablename__ = "integration_status"

    id = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    integration_type = Column(Enum(IntegrationType), nullable=False)

    # Status details
    status = Column(Enum(IntegrationState), default=IntegrationState.pending)
    error_message = Column(String, nullable=True)

    # ---- Sync tracking columns ----
    last_synced_at = Column(DateTime, nullable=True)  # last time the cron or sync ran
    next_sync_at = Column(DateTime, nullable=True)    # next scheduled sync time
    sync_interval_minutes = Column(Integer, default=60)  # e.g. run every 60 mins
    last_sync_duration = Column(Integer, nullable=True)  # duration in seconds (optional)
    total_syncs = Column(Integer, default=0)  # how many times sync has run

    # ---- Timestamps ----
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_checked = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "integration_type", name="unique_user_integration"),
    )

    # Relationships to config tables
    email_config = relationship("EmailConfig", back_populates="integration_status", uselist=False)
    whatsapp_config = relationship("WhatsappConfig", back_populates="integration_status", uselist=False)

    def __repr__(self):
        return (
            f"<IntegrationStatus(user_id={self.user_id}, type={self.integration_type}, "
            f"status={self.status}, next_sync_at={self.next_sync_at})>"
        )

# ---- Gmail Configuration Table ----
class EmailConfig(Base):
    __tablename__ = "email_config"

    id = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    integration_id = Column(  # 👇 clearer FK name
        PG_UUID(as_uuid=True),
        ForeignKey("integration_status.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    email_address = Column(String, nullable=False)
    provider = Column(String, default="gmail")
    credentials = Column(JSON, nullable=False)  # Encrypted OAuth tokens
    verified = Column(Boolean, default=False)
    connected_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to IntegrationStatus
    integration_status = relationship("IntegrationStatus", back_populates="email_config")

    def __repr__(self):
        return f"<EmailConfig(email={self.email_address}, verified={self.verified})>"


# ---- WhatsApp Configuration Table ----
class WhatsappConfig(Base):
    __tablename__ = "whatsapp_config"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(  # 👇 clearer FK name
        PG_UUID(as_uuid=True),
        ForeignKey("integration_status.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    phone_number = Column(String, nullable=False)
    business_id = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    connected_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to IntegrationStatus
    integration_status = relationship("IntegrationStatus", back_populates="whatsapp_config")

    def __repr__(self):
        return f"<WhatsappConfig(phone={self.phone_number}, verified={self.verified})>"
