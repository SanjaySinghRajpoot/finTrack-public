import base64
import logging
import io
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Union

import httpx
from fastapi import UploadFile

from app.models.models import Attachment, DocumentType, Email, SourceType
from app.services.db_service import DBService
from app.services.s3_service import S3Service
from app.services.file_service import FileService
from app.utils.utils import EmailMetadata, PDFTextExtractor, ProcessedAttachment, ProcessingFailure


class FileType(Enum):
    """Supported file types."""
    PDF = "pdf"


class ProcessingError(Exception):
    """Custom exception for file processing errors."""
    pass


class EmailAttachmentProcessor:
    """
    Processes attachments from Gmail or other sources:
    - Validates and decodes attachments
    - Uploads to S3 using S3Service
    - Extracts text content (PDFs only)
    """

    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
    SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp'}
    DEFAULT_MIME_TYPE = "application/pdf"

    def __init__(self, access_token, db: DBService, user_id: int, processed_batch_size: int, s3_service: Optional[S3Service] = None):
        """
        Initialize EmailAttachmentProcessor.

        Args:
            s3_service: Optional S3Service instance for dependency injection
        """
        self.logger = logging.getLogger(__name__)
        self.s3_service = s3_service or S3Service()
        self.text_extractor = PDFTextExtractor()
        self.db_service = db
        self.user_id = user_id
        self.processed_batch_size = processed_batch_size
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.file_service = FileService()

    async def _get(self, endpoint: str, params: dict = None) -> Dict:
        """Placeholder for your API get method."""
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self.headers, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            return {}

    def _decode_attachment(self, attachment_data: dict) -> bytes:
        """Decode base64 attachment data."""
        try:
            return base64.urlsafe_b64decode(attachment_data["data"])
        except (KeyError, ValueError) as e:
            raise ProcessingError(f"Failed to decode attachment data: {e}")

    def convert_to_processed_attachment(self, attachment: Attachment) -> ProcessedAttachment:
        """
        Convert an Attachment ORM object to a ProcessedAttachment instance.
        """
        return ProcessedAttachment(
            attachment_id=attachment.id,
            filename=attachment.filename,
            s3_key=attachment.s3_url,
            file_type=self.file_service._get_file_extension(attachment.filename),
            mime_type=attachment.mime_type or self.DEFAULT_MIME_TYPE,
            text_content=attachment.extracted_text,
            file_size=attachment.size,
        )

    async def _save_attachment(self, attachment_id, attachment_info, email_fk_id, filename):
        # Direct DB calls (sync) - no executor needed
        attachment_obj = self.db_service.get_attachment_by_id(attachment_id)

        if not attachment_obj:
            # Get the source_id from the email
            email = self.db_service.get_email_by_pk(email_fk_id)
            if not email or not email.source_id:
                raise ValueError(f"Email with id {email_fk_id} not found or has no source_id")
            
            attachment_obj = Attachment(
                source_id=email.source_id,  # Use source_id from email
                user_id=self.user_id,
                attachment_id=attachment_id,
                filename=filename,
                mime_type=attachment_info.get('mime_type'),
                size=attachment_info.get("file_size"),
                storage_path=attachment_info.get("file_path"),
                extracted_text=attachment_info.get("text_content"),
                s3_url=attachment_info.get("s3_key")
            )
            self.db_service.save_attachment(attachment_obj)
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
        filename = filename or self.file_service._generate_default_filename(attachment_id)

        try:
            # Validate file type
            if not self.file_service._is_supported_file(filename):
                raise ProcessingError(
                    f"Unsupported file type: {self.file_service._get_file_extension(filename)}"
                )

            # Decode attachment
            file_data = self._decode_attachment(attachment_data)

            # Upload to S3
            upload_file = self.file_service._create_upload_file(filename, file_data)
            s3_key = await self.s3_service.upload_file(upload_file)

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
                file_type=self.file_service._get_file_extension(filename),
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

    async def download_attachments(self, msg_id: str, email_obj: Email, payload: Dict) -> List[Dict]:
        try:
            """Download and process email attachments."""
            attachments = []

            if "parts" not in payload:
                return attachments

            for part in payload["parts"]:
                body = part.get("body", {})
                if "attachmentId" in body:  # it's an attachment
                    attachment_id = body["attachmentId"]

                    attachment_data = await self._get(f"messages/{msg_id}/attachments/{attachment_id}")
                    filename = part.get("filename")

                    attachment_info = await self.process_gmail_attachment(attachment_data, attachment_id, filename, email_id=email_obj.id)

                    attachments.append(attachment_info)
            return attachments
        except Exception as e:
            print(e)
            return [{}]
