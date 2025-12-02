import hashlib
from dataclasses import dataclass, field
from datetime import datetime
import io
import os
from typing import Optional, Tuple
from fastapi import UploadFile

import PyPDF2
from app.models.models import ProcessedEmailData
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# Load client secrets from Google Cloud Console
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = f"{os.getenv('HOST_URL', 'https://fintrack.rapidlabs.app')}/api/emails/oauth2callback"

class GmailOAuth:
    """Handles OAuth flow for Gmail."""

    @staticmethod
    def get_flow():
        """Create OAuth2 flow instance."""
        return Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

    @staticmethod
    def build_service(token_data: dict):
        """Build Gmail service from token data."""
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        return build("gmail", "v1", credentials=creds)


def create_processed_email_data(user_id: int, source_id: int, email_id: int, data: dict) -> ProcessedEmailData:
    """
    Creates a ProcessedEmailData object from the given dictionary and saves it to the DB.
    
    :param user_id: ID of the user owning the email
    :param source_id: ID of the source (primary reference)
    :param email_id: ID of the source email (kept for backward compatibility)
    :param data: Dictionary containing document information
    :return: ProcessedEmailData instance
    """
    def parse_date(date_str):
        if date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        return None

    processed_data = ProcessedEmailData(
        user_id=user_id,
        source_id=source_id,  # Primary reference now
        email_id=email_id,    # Keep for backward compatibility
        document_type=data.get("document_type"),
        title=data.get("title"),
        description=data.get("description"),
        document_number=data.get("document_number"),
        reference_id=data.get("reference_id"),
        issue_date=parse_date(data.get("issue_date")),
        due_date=parse_date(data.get("due_date")),
        payment_date=parse_date(data.get("payment_date")),
        amount=data.get("amount", 0.0),
        currency=data.get("currency", "INR"),
        is_paid=data.get("is_paid", False),
        payment_method=data.get("payment_method"),
        vendor_name=data.get("vendor_name"),
        vendor_gstin=data.get("vendor_gstin"),
        category=data.get("category"),
        tags=data.get("tags"),
        meta_data=data.get("metadata"),  # optional extra metadata
        file_url=data.get("file_url")
    )

    return processed_data

@dataclass
class EmailMetadata:
    """Email context for an attachment."""
    subject: str
    sender: str
    date: str
    message_id: str

    @classmethod
    def from_dict(cls, data: dict) -> "EmailMetadata":
        """Create from dictionary with safe defaults."""
        return cls(
            subject=data.get("subject", "")[:1000],
            sender=data.get("sender", ""),
            date=data.get("date", ""),
            message_id=data.get("message_id", ""),
        )


@dataclass
class ProcessedAttachment:
    """Result of successfully processing an attachment."""
    attachment_id: str
    filename: str
    s3_key: str
    file_type: str
    mime_type: str
    text_content: str
    file_size: int
    processed_at: datetime = field(default_factory=datetime.now)
    email_metadata: Optional[EmailMetadata] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses if needed."""
        result = {
            "attachment_id": self.attachment_id,
            "filename": self.filename,
            "s3_key": self.s3_key,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "text_content": self.text_content,
            "file_size": self.file_size,
            "processed_at": self.processed_at.isoformat(),
            "success": True,
        }

        if self.email_metadata:
            result.update({
                "email_subject": self.email_metadata.subject,
                "email_sender": self.email_metadata.sender,
                "email_date": self.email_metadata.date,
                "message_id": self.email_metadata.message_id,
            })

        return result


@dataclass
class ProcessingFailure:
    """Result of failed attachment processing."""
    attachment_id: str
    filename: str
    error: str
    processed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses if needed."""
        return {
            "attachment_id": self.attachment_id,
            "filename": self.filename,
            "success": False,
            "error": self.error,
            "processed_at": self.processed_at.isoformat(),
        }

class PDFTextExtractor:
    """Handles PDF text extraction logic."""

    @staticmethod
    def extract(file_data: bytes) -> str:
        """Extract text from PDF binary data."""
        text_pages = []

        with io.BytesIO(file_data) as pdf_stream:
            reader = PyPDF2.PdfReader(pdf_stream)

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_pages.append(text)

        return "\n".join(text_pages)


@dataclass
class DuplicateCheckResult:
    """Result of duplicate file check."""
    is_duplicate: bool
    existing_attachment_id: Optional[int] = None
    existing_filename: Optional[str] = None
    existing_source_id: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "is_duplicate": self.is_duplicate,
            "existing_attachment_id": self.existing_attachment_id,
            "existing_filename": self.existing_filename,
            "existing_source_id": self.existing_source_id
        }


class FileHashUtils:
    """Utility functions for file hashing and duplicate detection."""

    @staticmethod
    async def generate_file_hash(file: UploadFile) -> str:
        """
        Generate SHA-256 hash of the uploaded file content.

        Args:
            file: FastAPI UploadFile object

        Returns:
            str: Hexadecimal SHA-256 hash of the file content
        """
        # Create SHA-256 hash object
        sha256_hash = hashlib.sha256()

        # Read file in chunks to handle large files efficiently
        chunk_size = 8192  # 8KB chunks

        # Reset file position to beginning
        await file.seek(0)

        while chunk := await file.read(chunk_size):
            sha256_hash.update(chunk)

        # Reset file position back to beginning for further processing
        await file.seek(0)

        return sha256_hash.hexdigest()

    @staticmethod
    def generate_file_hash_from_bytes(file_content: bytes) -> str:
        """
        Generate SHA-256 hash from file content bytes.

        Args:
            file_content: File content as bytes

        Returns:
            str: Hexadecimal SHA-256 hash of the file content
        """
        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_content)
        return sha256_hash.hexdigest()
