import base64
import hashlib
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import PyPDF2
from fastapi import UploadFile

from app.models.models import Attachment, ManualUpload, DocumentType, SourceType
from app.services.db_service import DBService
from app.services.s3_service import S3Service
from app.utils.utils import EmailMetadata, PDFTextExtractor, ProcessedAttachment, ProcessingFailure, FileHashUtils


class FileType(Enum):
    """Supported file types."""
    PDF = "pdf"


class ProcessingError(Exception):
    """Custom exception for file processing errors."""
    pass

class FileProcessor:
    """
    Processes attachments from Gmail or other sources:
    - Validates and decodes attachments
    - Uploads to S3 using S3Service
    - Extracts text content (PDFs only)
    """

    SUPPORTED_EXTENSIONS = {".pdf"}
    DEFAULT_MIME_TYPE = "application/pdf"

    def __init__(self, db: DBService, user_id : int, s3_service: Optional[S3Service] = None):
        """
        Initialize FileProcessor.

        Args:
            s3_service: Optional S3Service instance for dependency injection
        """
        self.logger = logging.getLogger(__name__)
        self.s3_service = s3_service or S3Service()
        self.text_extractor = PDFTextExtractor()
        self.db_service = db
        self.user_id = user_id

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
        
    async def upload_file(self, file: UploadFile, user_id: int, document_type: str = "INVOICE", upload_notes: str = None):
        """
        Upload a file manually (for ManualUpload table).
        
        Args:
            file: FastAPI UploadFile object
            user_id: ID of the user uploading the file
            document_type: Type of document being uploaded
            upload_notes: Optional notes about the upload
            
        Returns:
            dict: Upload result with attachment and manual upload info
        """
        try:
            # Validate file type
            if not self._is_supported_file(file.filename):
                raise ProcessingError(
                    f"Unsupported file type: {self._get_file_extension(file.filename)}"
                )

            # Read file data
            file_data = await file.read()
            
            # Upload to S3
            s3_key = await self.s3_service.upload_pdf(file)
            
            # Extract text content
            text_content = self.text_extractor.extract(file_data)
            
            # First create ManualUpload entry (this will trigger the event handler to create Source)
            manual_upload = ManualUpload(
                user_id=user_id,
                document_type=DocumentType[document_type.upper()],
                upload_method="web_upload",
                upload_notes=upload_notes
            )
            self.db_service.add(manual_upload)
            self.db_service.flush()  # This triggers the event handler to create Source
            
            # Get the created source from the event handler
            # The event handler creates a Source with type=manual and external_id=manual_upload.id
            from app.models.models import Source
            source = self.db_service.db.query(Source).filter(
                Source.type == "manual",
                Source.external_id == str(manual_upload.id)
            ).first()
            
            if not source:
                raise ProcessingError("Failed to create source for manual upload")
            
            # Now create the Attachment with the source_id
            attachment = Attachment(
                source_id=source.id,
                user_id=user_id,
                attachment_id=f"manual_{user_id}_{int(datetime.now().timestamp())}",
                filename=file.filename,
                mime_type=file.content_type or self.DEFAULT_MIME_TYPE,
                size=len(file_data),
                storage_path=None,  # Using S3
                s3_url=s3_key,
                extracted_text=text_content
            )
            self.db_service.add(attachment)
            self.db_service.flush()  # Get the attachment ID
            
            self.db_service.commit()

            self.logger.info(
                f"Successfully uploaded file: {file.filename} (size: {len(file_data)} bytes) for user {user_id}"
            )
            
            return {
                "success": True,
                "attachment_id": attachment.id,
                "manual_upload_id": manual_upload.id,
                "filename": file.filename,
                "s3_key": s3_key,
                "file_size": len(file_data),
                "document_type": document_type
            }
            
        except ProcessingError as e:
            self.db_service.db.rollback()
            self.logger.error(f"Processing error for {file.filename}: {e}")
            raise e
        except Exception as e:
            self.db_service.db.rollback()
            self.logger.exception(f"Unexpected error processing {file.filename}")
            raise ProcessingError(f"Upload failed: {str(e)}")

    async def upload_file_with_hash(self, file: UploadFile, user_id: int, document_type: str = "INVOICE", upload_notes: str = None, file_hash: str = None):
        """
        Upload a file manually with hash storage for duplicate detection.
        
        Args:
            file: FastAPI UploadFile object
            user_id: ID of the user uploading the file
            document_type: Type of document being uploaded
            upload_notes: Optional notes about the upload
            file_hash: SHA-256 hash of the file content
            
        Returns:
            dict: Upload result with attachment and manual upload info
        """
        try:
            # Validate file type
            if not self._is_supported_file(file.filename):
                raise ProcessingError(
                    f"Unsupported file type: {self._get_file_extension(file.filename)}"
                )

            # Read file data
            file_data = await file.read()
            
            # Generate hash if not provided
            if not file_hash:
                file_hash = FileHashUtils.generate_file_hash_from_bytes(file_data)
            
            # Upload to S3
            s3_key = await self.s3_service.upload_pdf(file)
            
            # Extract text content
            text_content = self.text_extractor.extract(file_data)
            
            # First create ManualUpload entry (this will trigger the event handler to create Source)
            manual_upload = ManualUpload(
                user_id=user_id,
                document_type=DocumentType[document_type.upper()],
                upload_method="web_upload",
                upload_notes=upload_notes
            )
            self.db_service.add(manual_upload)
            self.db_service.flush()  # This triggers the event handler to create Source
            
            # Get the created source from the event handler
            # The event handler creates a Source with type=manual and external_id=manual_upload.id
            from app.models.models import Source
            source = self.db_service.db.query(Source).filter(
                Source.type == "manual",
                Source.external_id == str(manual_upload.id)
            ).first()
            
            if not source:
                raise ProcessingError("Failed to create source for manual upload")
            
            # Now create the Attachment with the source_id and file hash
            attachment = Attachment(
                source_id=source.id,
                user_id=user_id,
                attachment_id=f"manual_{user_id}_{int(datetime.now().timestamp())}",
                filename=file.filename,
                mime_type=file.content_type or self.DEFAULT_MIME_TYPE,
                size=len(file_data),
                file_hash=file_hash,  # Store the file hash
                storage_path=None,  # Using S3
                s3_url=s3_key,
                extracted_text=text_content
            )
            self.db_service.add(attachment)
            self.db_service.flush()  # Get the attachment ID
            
            self.db_service.commit()

            self.logger.info(
                f"Successfully uploaded file with hash: {file.filename} (size: {len(file_data)} bytes, hash: {file_hash[:16]}...) for user {user_id}"
            )
            
            return {
                "success": True,
                "attachment_id": attachment.id,
                "manual_upload_id": manual_upload.id,
                "filename": file.filename,
                "s3_key": s3_key,
                "file_size": len(file_data),
                "document_type": document_type,
                "file_hash": file_hash
            }
            
        except ProcessingError as e:
            self.db_service.db.rollback()
            self.logger.error(f"Processing error for {file.filename}: {e}")
            raise e
        except Exception as e:
            self.db_service.db.rollback()
            self.logger.exception(f"Unexpected error processing {file.filename}")
            raise ProcessingError(f"Upload failed: {str(e)}")