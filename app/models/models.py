from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
import json

class Base(DeclarativeBase):
    pass 

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
    metadata = Column(JSON, nullable=True)           # raw Gmail payload metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    attachments = relationship("Attachment", back_populates="email")
        



class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)

    filename = Column(String(512), nullable=False)
    mime_type = Column(String(255), nullable=True)
    size = Column(Integer, nullable=True)

    # storage references
    storage_path = Column(String(1024), nullable=True)  # S3/GCS/Local path
    extracted_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    email = relationship("Email", back_populates="attachments")
