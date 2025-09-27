from sqlalchemy import (
    Column, Integer, String, Float, Date, Enum, Text, ForeignKey, Boolean,
    DateTime, JSON, func
)
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


class ProcessedEmailData(Base):
    __tablename__ = "processed_email_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # link to user (redundant but useful for quick queries)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # link back to the source email
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)

    document_type = Column(Enum(DocumentType), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    document_number = Column(String(100), nullable=True)
    reference_id = Column(String(100), nullable=True)

    issue_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)

    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")

    is_paid = Column(Boolean, default=False)
    payment_method = Column(String(50), nullable=True)

    vendor_name = Column(String(255), nullable=True)
    vendor_gstin = Column(String(50), nullable=True)

    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)

    file_url = Column(String(500), nullable=True)
    meta_data = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships