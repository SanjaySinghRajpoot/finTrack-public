import base64
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import PyPDF2
from fastapi import UploadFile

from app.models.models import Attachment
from app.services.db_service import DBService
from app.services.s3_service import S3Service


class FileType(Enum):
    """Supported file types."""
    PDF = "pdf"


class ProcessingError(Exception):
    """Custom exception for file processing errors."""
    pass


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


class FileProcessor:
    """
    Processes attachments from Gmail or other sources:
    - Validates and decodes attachments
    - Uploads to S3 using S3Service
    - Extracts text content (PDFs only)
    """

    SUPPORTED_EXTENSIONS = {".pdf"}
    DEFAULT_MIME_TYPE = "application/pdf"

    def __init__(self, db: DBService, s3_service: Optional[S3Service] = None):
        """
        Initialize FileProcessor.

        Args:
            s3_service: Optional S3Service instance for dependency injection
        """
        self.logger = logging.getLogger(__name__)
        self.s3_service = s3_service or S3Service()
        self.text_extractor = PDFTextExtractor()
        self.db = db

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension without the dot."""
        return Path(filename).suffix.lower().lstrip(".")

    def _is_supported_file(self, filename: str) -> bool:
        """Check if file type is supported."""
        return Path(filename).suffix.lower() in self.SUPPORTED_EXTENSIONS

    def _decode_attachment(self, attachment_data: dict) -> bytes:
        """Decode base64 attachment data."""
        try:
            return base64.urlsafe_b64decode(attachment_data["data"])
        except (KeyError, ValueError) as e:
            raise ProcessingError(f"Failed to decode attachment data: {e}")

    def  _create_upload_file(self, filename: str, file_data: bytes) -> UploadFile:
        """Create FastAPI UploadFile object from bytes."""
        return UploadFile(filename=filename, file=io.BytesIO(file_data))

    def _generate_default_filename(self, attachment_id: str) -> str:
        """Generate default filename if none provided."""
        return f"attachment_{attachment_id}.pdf"

    def convert_to_processed_attachment(self, attachment: Attachment) -> ProcessedAttachment:
        """
        Convert an Attachment ORM object to a ProcessedAttachment instance.
        """
        return ProcessedAttachment(
            attachment_id=attachment.id,
            filename=attachment.filename,
            s3_key=attachment.s3_url,
            file_type=self._get_file_extension(attachment.filename),
            mime_type=attachment.mime_type or self.DEFAULT_MIME_TYPE,
            text_content=attachment.extracted_text,
            file_size=attachment.size,
        )

    async def _save_attachment(self, attachment_id, attachment_info, email_fk_id, filename):
        attachment_obj = self.db.get_attachment_by_id(attachment_id)

        if not attachment_obj:
            # Get the source_id from the email
            email = self.db.get_email_by_pk(email_fk_id)
            if not email or not email.source_id:
                raise ValueError(f"Email with id {email_fk_id} not found or has no source_id")
            
            attachment_obj = Attachment(
                source_id=email.source_id,  # Use source_id from email
                attachment_id=attachment_id,
                filename=filename,
                mime_type=attachment_info.get('mime_type'),
                size=attachment_info.get("file_size"),
                storage_path=attachment_info.get("file_path"),
                extracted_text=attachment_info.get("text_content"),
                s3_url=attachment_info.get("s3_key")
            )
            self.db.save_attachment(attachment_obj)
        else:
            print("attachment already exists, skipping ")

    async def process_gmail_attachment(
            self,
            attachment_data: dict,
            attachment_id: str,
            filename: Optional[str] = None,
            msg_metadata: Optional[dict] = None,
            email_id: int = None,
    ) -> dict:
        """
        Process a Gmail attachment.

        Args:
            attachment_data: Dictionary containing base64-encoded 'data' key
            attachment_id: Unique identifier for the attachment
            filename: Original filename (optional)
            msg_metadata: Email metadata dictionary (optional)
            email_id: email fk

        Returns:
            ProcessedAttachment on success, ProcessingFailure on error
        """
        filename = filename or self._generate_default_filename(attachment_id)

        try:
            # Validate file type
            if not self._is_supported_file(filename):
                raise ProcessingError(
                    f"Unsupported file type: {self._get_file_extension(filename)}"
                )

            # Decode attachment
            file_data = self._decode_attachment(attachment_data)

            # Upload to S3
            upload_file = self._create_upload_file(filename, file_data)
            s3_key = await self.s3_service.upload_pdf(upload_file)

            # Extract text content
            text_content = self.text_extractor.extract(file_data)

            # Parse email metadata if provided
            email_meta = None
            if msg_metadata:
                email_meta = EmailMetadata.from_dict(msg_metadata)

            # Create success result
            result = ProcessedAttachment(
                attachment_id=attachment_id,
                filename=filename,
                s3_key=s3_key,
                file_type=self._get_file_extension(filename),
                mime_type=self.DEFAULT_MIME_TYPE,
                text_content=text_content,
                file_size=len(file_data),
                email_metadata=email_meta,
            )

            self.logger.info(
                f"Successfully processed attachment: {filename} (size: {len(file_data)} bytes)"
            )

            await self._save_attachment(attachment_id, result.to_dict(), email_id, filename)

            return result.to_dict()

        except ProcessingError as e:
            self.logger.error(f"Processing error for {filename}: {e}")
            return ProcessingFailure(
                attachment_id=attachment_id,
                filename=filename,
                error=str(e),
            ).to_dict()
        except Exception as e:
            self.logger.exception(f"Unexpected error processing {filename}")
            return ProcessingFailure(
                attachment_id=attachment_id,
                filename=filename,
                error=f"Unexpected error: {str(e)}",
            ).to_dict()