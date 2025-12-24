import base64
import hashlib
import io
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple

import PyPDF2
from fastapi import UploadFile

from app.models.models import Attachment, ManualUpload, DocumentType, SourceType
from app.services.db_service import DBService
from app.services.s3_service import S3Service
from app.utils.utils import FileHashUtils, PDFTextExtractor



class FileType(Enum):
    """Supported file types."""
    PDF = "pdf"


class ProcessingError(Exception):
    """Custom exception for file processing errors."""
    pass


class FileService:
    """
    Provides utility functions for file operations.
    """
    SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp'}

    def _create_upload_file(self, filename: str, file_data: bytes) -> UploadFile:
        """Create FastAPI UploadFile object from bytes."""
        return UploadFile(filename=filename, file=io.BytesIO(file_data))

    def _generate_default_filename(self, attachment_id: str) -> str:
        """Generate default filename if none provided."""
        return f"attachment_{attachment_id}.pdf"

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension without the dot."""
        return Path(filename).suffix.lower().lstrip(".")

    def _is_supported_file(self, filename: str) -> bool:
        """Check if file type is supported."""
        return Path(filename).suffix.lower() in self.SUPPORTED_EXTENSIONS


class FileProcessor:
    """
    Processes files for manual uploads and provides utilities for file handling.
    """
    DEFAULT_MIME_TYPE = "application/pdf"

    def __init__(self, db: DBService, user_id : int, s3_service: Optional[S3Service] = None, file_service: Optional[FileService] = None):
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
        self.file_service = file_service or FileService()

    async def _validate_and_read_file(self, file: UploadFile) -> bytes:
        if not self.file_service._is_supported_file(file.filename):
            raise ProcessingError(
                f"Unsupported file type: {self.file_service._get_file_extension(file.filename)}"
            )
        return await file.read()

    def _generate_or_validate_hash(self, file_data: bytes, file_hash: Optional[str] = None) -> str:
        if file_hash:
            return file_hash
        return FileHashUtils.generate_file_hash_from_bytes(file_data)

    async def _upload_to_s3(self, file: UploadFile) -> str:
        return await self.s3_service.upload_file(file)

    def _create_manual_upload_entry(self, user_id: int, document_type: str, upload_notes: Optional[str] = None) -> ManualUpload:
        """
        Create ManualUpload database entry.
        
        Args:
            user_id: ID of the user
            document_type: Type of document
            upload_notes: Optional notes
            
        Returns:
            ManualUpload: Created manual upload object
        """
        manual_upload = ManualUpload(
            user_id=user_id,
            document_type=DocumentType[document_type.upper()],
            upload_method="web_upload",
            upload_notes=upload_notes
        )
        self.db_service.add(manual_upload)
        self.db_service.flush()
        return manual_upload

    def _get_source_from_manual_upload(self, manual_upload_id: int):
        from app.models.models import Source
        source = self.db_service.db.query(Source).filter(
            Source.type == "manual",
            Source.external_id == str(manual_upload_id)
        ).first()
        
        if not source:
            raise ProcessingError("Failed to create source for manual upload")
        
        return source

    def _create_attachment_entry(
        self, 
        source_id: int,
        user_id: int,
        filename: str,
        file_data: bytes,
        s3_key: str,
        file_hash: str,
        mime_type: Optional[str] = None,
        extracted_text: Optional[str] = None
    ) -> Attachment:
        """
        Create Attachment database entry.
        
        Args:
            source_id: ID of the source
            user_id: ID of the user
            filename: Name of the file
            file_data: File content (for size calculation)
            s3_key: S3 storage key
            file_hash: SHA-256 hash of the file
            mime_type: Optional MIME type
            extracted_text: Optional extracted text content
            
        Returns:
            Attachment: Created attachment object
        """
        attachment = Attachment(
            source_id=source_id,
            user_id=user_id,
            attachment_id=f"manual_{user_id}_{int(datetime.now().timestamp())}",
            filename=filename,
            mime_type=mime_type or self.DEFAULT_MIME_TYPE,
            size=len(file_data) if file_data else None,
            file_hash=file_hash,
            storage_path=None,
            s3_url=s3_key,
            extracted_text=extracted_text
        )
        self.db_service.add(attachment)
        self.db_service.flush()
        return attachment

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
            if not self.file_service._is_supported_file(file.filename):
                raise ProcessingError(
                    f"Unsupported file type: {self.file_service._get_file_extension(file.filename)}"
                )

            # Read file data
            file_data = await file.read()
            
            # Upload to S3
            upload_file = self.file_service._create_upload_file(file.filename, file_data)
            s3_key = await self.s3_service.upload_file(upload_file)
            
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

    async def upload_file_with_hash(self, file: UploadFile, file_hash: Optional[str] = None) -> dict:
        """
        Upload a file with hash generation - only handles file validation, hashing, and S3 upload.
        Database operations should be handled by the caller.
        
        Args:
            file: FastAPI UploadFile object
            file_hash: Optional pre-computed SHA-256 hash of the file content
            
        Returns:
            dict: Upload result with file_hash, s3_key, file_data, and file_size
            
        Raises:
            ProcessingError: If validation or upload fails
        """
        try:
            # Step 1: Validate and read file
            file_data = await self._validate_and_read_file(file)
            
            # Step 2: Generate or validate file hash
            file_hash = self._generate_or_validate_hash(file_data, file_hash)
            
            # Step 3: Upload to S3
            upload_file = self.file_service._create_upload_file(file.filename, file_data)
            s3_key = await self.s3_service.upload_file(upload_file)

            self.logger.info(
                f"Successfully uploaded file to S3: {file.filename} "
                f"(size: {len(file_data)} bytes, hash: {file_hash[:16]}...)"
            )
            
            return {
                "file_hash": file_hash,
                "s3_key": s3_key,
                "file_data": file_data,
                "file_size": len(file_data),
                "filename": file.filename,
                "mime_type": file.content_type or self.DEFAULT_MIME_TYPE
            }
            
        except ProcessingError as e:
            self.logger.error(f"Processing error for {file.filename}: {e}")
            raise e
        except Exception as e:
            self.logger.exception(f"Unexpected error processing {file.filename}")
            raise ProcessingError(f"Upload failed: {str(e)}")
    
    def extract_text(self, file_data: bytes) -> Optional[str]:
        """
        Extract text content from file data.
        
        Args:
            file_data: File content as bytes
            
        Returns:
            Optional[str]: Extracted text content or None
        """
        try:
            return self.text_extractor.extract(file_data)
        except Exception as e:
            self.logger.warning(f"Text extraction failed: {e}")
            return None


class DocumentProcessor:
    """
    Handles document processing using OCR and LLM services.
    Implements separation of concerns for document analysis.
    """
    
    def __init__(self, db_service: DBService, user_id: int):
        """
        Initialize DocumentProcessor.
        
        Args:
            db_service: Database service instance
            user_id: ID of the user
        """
        self.db_service = db_service
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        self.DEFAULT_MIME_TYPE = "application/pdf"
        
    def _is_pdf(self, filename: str) -> bool:
        """Check if file is a PDF."""
        return filename.lower().endswith('.pdf')
    
    def _is_image(self, filename: str) -> bool:
        """Check if file is an image."""
        return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
    
    async def process_with_ocr(
        self, 
        file_data: bytes, 
        filename: str, 
        source_id: int, 
        document_type: str
    ) -> Optional[dict]:
        """
        Process document using OCR service.
        
        Args:
            file_data: File content as bytes
            filename: Name of the file
            source_id: Source ID in database
            document_type: Type of document
            
        Returns:
            Optional[dict]: OCR result or None if OCR fails/unavailable
        """
        temp_file_path = None
        try:
            from app.services.ocr import OCRService
            
            # Pass user_id to OCRService for custom schema support
            ocr_service = OCRService(self.db_service.db, self.user_id)
            
            if not ocr_service.is_available():
                self.logger.info("OCR service not available")
                return None
            
            self.logger.info(f"Attempting OCR processing for {filename}")
            
            suffix = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(file_data)
                temp_file_path = tmp_file.name
            
            ocr_result = await ocr_service.process_document(
                file_path=temp_file_path,
                filename=filename,
                source_id=source_id,
                user_id=self.user_id,
                document_type=document_type.lower()
            )
            
            if ocr_result:
                self.logger.info(f"OCR processing successful for {filename}")
                return ocr_result
            else:
                self.logger.warning(f"OCR processing failed for {filename}")
                return None
                
        except Exception as e:
            self.logger.warning(f"OCR processing error: {e}")
            return None
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    self.logger.debug(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    self.logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
    
    async def process_pdf_with_llm(
        self,
        text_content: str,
        source_id: int,
        filename: str,
        s3_key: str,
        upload_notes: Optional[str] = None,
        file_hash: Optional[str] = None
    ) -> List[dict]:
        try:
            from app.services.llm_service import LLMService, DocumentProcessingRequest
            
            llm_service = LLMService(self.user_id, self.db_service)
            
            processing_request = DocumentProcessingRequest(
                source_id=source_id,
                user_id=self.user_id,
                document_type="manual_upload",
                text_content=text_content,
                metadata={
                    "filename": filename,
                    "s3_key": s3_key,
                    "upload_method": "web_upload",
                    "upload_notes": upload_notes,
                    "file_hash": file_hash
                }
            )
            
            results = llm_service.llm_manual_processing([processing_request])
            self.logger.info(f"LLM PDF processing completed with {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"LLM PDF processing failed: {e}")
            return []
    
    async def process_image_with_llm(
        self,
        image_base64: str,
        source_id: int,
        filename: str,
        s3_key: str,
        mime_type: str,
        upload_notes: Optional[str] = None,
        file_hash: Optional[str] = None
    ) -> List[dict]:
        """
        Process image document using LLM service.
        
        Args:
            image_base64: Base64-encoded image data
            source_id: Source ID in database
            filename: Name of the file
            s3_key: S3 storage key
            mime_type: MIME type of the image
            upload_notes: Optional upload notes
            file_hash: Optional file hash
            
        Returns:
            List[dict]: LLM processing results
        """
        try:
            from app.services.llm_service import LLMService, DocumentProcessingRequest
            
            llm_service = LLMService(self.user_id, self.db_service)
            
            processing_request = DocumentProcessingRequest(
                source_id=source_id,
                user_id=self.user_id,
                document_type="manual_upload",
                image_base64=image_base64,
                metadata={
                    "filename": filename,
                    "s3_key": s3_key,
                    "upload_method": "web_upload",
                    "upload_notes": upload_notes,
                    "file_hash": file_hash,
                    "mime_type": mime_type
                }
            )
            
            results = llm_service.llm_image_processing_batch([processing_request])
            self.logger.info(f"LLM image processing completed with {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"LLM image processing failed: {e}")
            return []
    
    async def process_document(
        self,
        file_data: bytes,
        filename: str,
        source_id: int,
        document_type: str,
        text_content: Optional[str] = None,
        s3_key: Optional[str] = None,
        upload_notes: Optional[str] = None,
        file_hash: Optional[str] = None
    ) -> Tuple[bool, List[dict], str]:
        ocr_success = False
        processing_results = []
        processing_method = "none"
        
        # Removed for now as want to process entirely with the llm model
        # ocr_result = await self.process_with_ocr(
        #     file_data=file_data,
        #     filename=filename,
        #     source_id=source_id,
        #     document_type=document_type
        # )
        
        # if ocr_result:
        #     ocr_success = True
        #     processing_results = [ocr_result]
        #     processing_method = "ocr"
        #     return ocr_success, processing_results, processing_method
        
        self.logger.info(f"Falling back to LLM processing for {filename}")
        
        if self._is_pdf(filename) and text_content:
            processing_results = await self.process_pdf_with_llm(
                text_content=text_content,
                source_id=source_id,
                filename=filename,
                s3_key=s3_key or "",
                upload_notes=upload_notes,
                file_hash=file_hash
            )
            processing_method = "llm_pdf"
            
        elif self._is_image(filename):
            image_base64 = base64.b64encode(file_data).decode("utf-8")
            processing_results = await self.process_image_with_llm(
                image_base64=image_base64,
                source_id=source_id,
                filename=filename,
                s3_key=s3_key or "",
                mime_type=self.DEFAULT_MIME_TYPE,
                upload_notes=upload_notes,
                file_hash=file_hash
            )
            processing_method = "llm_image"
        
        return ocr_success, processing_results, processing_method