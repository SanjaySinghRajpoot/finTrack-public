import logging
from datetime import datetime
from typing import Optional

from fastapi import UploadFile

from app.models.models import Attachment, ManualUpload, DocumentType
from app.services.db_service import DBService
from app.services.s3_service import S3Service
from app.services.file_service import FileService, ProcessingError
from app.utils.utils import FileHashUtils, PDFTextExtractor


class FileProcessor:
    """Handles file upload, validation, hashing, S3 storage, and attachment creation."""
    
    DEFAULT_MIME_TYPE = "application/pdf"

    def __init__(self, db: DBService, user_id: int, s3_service: Optional[S3Service] = None, file_service: Optional[FileService] = None):
        self.logger = logging.getLogger(__name__)
        self.s3_service = s3_service or S3Service()
        self.text_extractor = PDFTextExtractor()
        self.db_service = db
        self.user_id = user_id
        self.file_service = file_service or FileService()

    async def _validate_and_read_file(self, file: UploadFile) -> bytes:
        """Validate file type and read file data."""
        if not self.file_service._is_supported_file(file.filename):
            raise ProcessingError(
                f"Unsupported file type: {self.file_service._get_file_extension(file.filename)}"
            )
        return await file.read()

    def _generate_or_validate_hash(self, file_data: bytes, file_hash: Optional[str] = None) -> str:
        """Generate file hash or validate provided hash."""
        if file_hash:
            return file_hash
        return FileHashUtils.generate_file_hash_from_bytes(file_data)

    async def _upload_to_s3(self, file: UploadFile) -> str:
        """Upload file to S3 and return key."""
        return await self.s3_service.upload_file(file)

    def _create_manual_upload_entry(self, user_id: int, document_type: str, upload_notes: Optional[str] = None) -> ManualUpload:
        """Create manual upload database entry."""
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
        """Retrieve source record associated with manual upload."""
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
        """Create attachment database entry."""
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
        """Upload file with full database integration (manual upload + attachment)."""
        try:
            if not self.file_service._is_supported_file(file.filename):
                raise ProcessingError(
                    f"Unsupported file type: {self.file_service._get_file_extension(file.filename)}"
                )

            file_data = await file.read()
            
            upload_file = self.file_service._create_upload_file(file.filename, file_data)
            s3_key = await self.s3_service.upload_file(upload_file)
            
            text_content = self.text_extractor.extract(file_data)
            
            # Use helper method to create manual upload
            manual_upload = self._create_manual_upload_entry(
                user_id=user_id,
                document_type=document_type.upper(),
                upload_notes=upload_notes
            )
            
            # Use helper method to get source
            source = self._get_source_from_manual_upload(manual_upload.id)
            
            # Use helper method to create attachment
            attachment = self._create_attachment_entry(
                source_id=source.id,
                user_id=user_id,
                filename=file.filename,
                file_data=file_data,
                s3_key=s3_key,
                file_hash=FileHashUtils.generate_file_hash_from_bytes(file_data),
                mime_type=file.content_type or self.DEFAULT_MIME_TYPE,
                extracted_text=text_content
            )
            
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
        """Handles file validation, hashing, and S3 upload. Database operations handled by caller."""
        try:
            file_data = await self._validate_and_read_file(file)
            file_hash = self._generate_or_validate_hash(file_data, file_hash)
            
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
        """Extract text content from file data."""
        try:
            return self.text_extractor.extract(file_data)
        except Exception as e:
            self.logger.warning(f"Text extraction failed: {e}")
            return None
