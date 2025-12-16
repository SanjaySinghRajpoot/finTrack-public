import logging
from starlette.responses import JSONResponse

from app.constants.integration_constants import FeatureKey
from app.services.s3_service import S3Service
from app.services.db_service import DBService
from app.models.scheme import UploadSuccessResponse, UploadSuccessData, UploadErrorResponse
from app.utils.exceptions import NotFoundError, ExternalServiceError, DatabaseError
from app.utils.decorators import deduct_credits

# Configure logger
logger = logging.getLogger(__name__)


class FileController:

    @staticmethod
    async def get_attachment(email_id: int, db):
        try:
            db_service = DBService(db)
            # Get attachments by email_id (which internally finds source_id)
            attachments = db_service.get_attachments_by_email_id(email_id)
            return attachments[0] if attachments else None
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve attachment: {str(e)}")
    
    @staticmethod
    async def get_presigned_upload_urls(payload, user, db):
        """
        Generate presigned URLs for direct S3 upload.
        Check for duplicate files by hash before generating URLs.
        
        Args:
            payload: PresignedUrlRequest containing list of files
            user: Authenticated user
            db: Database session
            
        Returns:
            PresignedUrlResponse with URLs or duplicate remarks
        """
        try:
            from datetime import datetime
            from app.models.scheme import PresignedUrlData, PresignedUrlResponse
            
            logger.info(f"🔵 Presigned URL request from user_id: {user.get('user_id')}, files count: {len(payload.files)}")
            
            db_service = DBService(db)
            s3_service = S3Service()
            user_id = user.get("user_id")
            
            response_data = []
            
            for idx, file_request in enumerate(payload.files):
                logger.info(f"📄 Processing file {idx + 1}/{len(payload.files)}: {file_request.filename}")
                logger.debug(f"   Hash: {file_request.file_hash[:16]}..., ContentType: {file_request.content_type}, Size: {file_request.file_size}")
                
                # Check if file with this hash already exists for this user
                duplicate_check = db_service.check_duplicate_file_by_hash(
                    file_request.file_hash, 
                    user_id
                )
                
                if duplicate_check.is_duplicate:
                    # File is duplicate, don't generate presigned URL
                    logger.warning(f"⚠️  Duplicate file detected: {file_request.filename} (attachment_id: {duplicate_check.attachment_id})")
                    response_data.append(PresignedUrlData(
                        filename=file_request.filename,
                        file_hash=file_request.file_hash,
                        presigned_url=None,
                        s3_key=None,
                        remark="duplicate",
                        duplicate_attachment_id=duplicate_check.attachment_id
                    ))
                else:
                    # File is new, generate presigned URL
                    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                    s3_key = f"attachments/{user_id}/{timestamp}_{file_request.filename}"
                    
                    logger.info(f"🔑 Generating presigned URL for S3 key: {s3_key}")
                    
                    presigned_url = await s3_service.generate_upload_presigned_url(
                        file_key=s3_key,
                        content_type=file_request.content_type,
                        expires_in=3600  # 1 hour
                    )
                    
                    logger.info(f"✅ Presigned URL generated successfully for: {file_request.filename}")
                    
                    response_data.append(PresignedUrlData(
                        filename=file_request.filename,
                        file_hash=file_request.file_hash,
                        presigned_url=presigned_url,
                        s3_key=s3_key,
                        remark="success",
                        duplicate_attachment_id=None
                    ))
            
            logger.info(f"✅ Presigned URL generation complete. Success: {sum(1 for d in response_data if d.remark == 'success')}, Duplicates: {sum(1 for d in response_data if d.remark == 'duplicate')}")
            
            return PresignedUrlResponse(
                message="Presigned URLs generated successfully",
                data=response_data
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URLs: {type(e).__name__} - {str(e)}", exc_info=True)
            raise ExternalServiceError("S3", f"Failed to generate presigned URLs: {str(e)}")
    
    @staticmethod
    @deduct_credits(feature_key=FeatureKey.FILE_UPLOAD.value)
    async def process_uploaded_files_metadata(**kwargs):
        """
        Process metadata for files that were uploaded directly to S3.
        Create attachment, manual_upload, and document_staging entries.
        Documents will be processed asynchronously by the cron job.
        
        Args:
            payload: FileMetadataRequest containing list of file metadata
            user: Authenticated user
            db: Database session
            
        Returns:
            FileMetadataResponse with created attachment and manual_upload IDs
        """
        payload = kwargs.get('payload')
        user = kwargs.get('user')
        db = kwargs.get('db')
        
        try:
            from app.models.scheme import ProcessedFileData, FileMetadataResponse
            from app.services.file_service import FileProcessor
            from app.models.models import DocumentStaging
            
            db_service = DBService(db)
            user_id = user.get("user_id")
            file_processor = FileProcessor(db_service, user_id)
            
            response_data = []
            
            for file_meta in payload.files:
                # Check if attachment already exists for this hash
                duplicate_check = db_service.check_duplicate_file_by_hash(
                    file_meta.file_hash, 
                    user_id
                )
                
                if duplicate_check.is_duplicate:
                    # File already exists, return existing IDs
                    response_data.append(ProcessedFileData(
                        filename=file_meta.filename,
                        file_hash=file_meta.file_hash,
                        attachment_id=duplicate_check.attachment_id,
                        manual_upload_id=duplicate_check.manual_upload_id or 0,
                        status="existing"
                    ))
                    continue
                
                # Create manual upload entry
                manual_upload = file_processor._create_manual_upload_entry(
                    user_id=user_id,
                    document_type=file_meta.document_type.upper(),
                    upload_notes=file_meta.upload_notes
                )
                
                # Get or create source for this manual upload
                source = file_processor._get_source_from_manual_upload(manual_upload.id)
                
                # Create attachment entry with S3 key from metadata
                attachment = file_processor._create_attachment_entry(
                    source_id=source.id,
                    user_id=user_id,
                    filename=file_meta.filename,
                    file_data=None,  # File is already in S3
                    s3_key=file_meta.s3_key,
                    file_hash=file_meta.file_hash,
                    mime_type=file_meta.content_type,
                    extracted_text=None  # Will be extracted during processing
                )
                
                # Create DocumentStaging entry for async processing
                document_staging = DocumentStaging(
                    user_id=user_id,
                    source_id=source.id,
                    attachment_id=attachment.id,
                    manual_upload_id=manual_upload.id,
                    filename=file_meta.filename,
                    file_hash=file_meta.file_hash,
                    s3_key=file_meta.s3_key,
                    mime_type=file_meta.content_type,
                    file_size=file_meta.file_size,
                    document_type=file_meta.document_type,
                    source_type="manual",
                    upload_notes=file_meta.upload_notes,
                    document_processing_status="pending",
                    meta_data={
                        "upload_method": "direct_s3",
                        "content_type": file_meta.content_type
                    }
                )
                db_service.add(document_staging)
                
                db_service.commit()
                
                response_data.append(ProcessedFileData(
                    filename=file_meta.filename,
                    file_hash=file_meta.file_hash,
                    attachment_id=attachment.id,
                    manual_upload_id=manual_upload.id,
                    status="queued_for_processing"
                ))
            
            return FileMetadataResponse(
                message="Files queued for processing successfully",
                data=response_data
            )
            
        except Exception as e:
            raise DatabaseError(f"Failed to process file metadata: {str(e)}")
        
    @staticmethod
    @deduct_credits(feature_key=FeatureKey.FILE_UPLOAD.value)
    async def upload_file(**kwargs):
        """
        Upload a PDF file or image manually for a user with complete validation and error handling.
        """
        file = kwargs.get('file')
        user = kwargs.get('user')
        db = kwargs.get('db')
        document_type = kwargs.get('document_type', 'INVOICE')
        upload_notes = kwargs.get('upload_notes')
        
        try:
            from app.services.file_service import FileProcessor, FileHashUtils, DocumentProcessor
            
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.webp'}
            file_extension = file.filename.lower()
            
            if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                error_response = UploadErrorResponse(error="Only PDF and image files (JPG, PNG, WEBP) are supported")
                return JSONResponse(
                    status_code=400, 
                    content=error_response.dict()
                )
            
            is_pdf = file_extension.endswith('.pdf')
            is_image = file_extension.endswith(('.jpg', '.jpeg', '.png', '.webp'))
            
            MAX_FILE_SIZE = 10 * 1024 * 1024
            file_content = await file.read()
            if (len(file_content) > MAX_FILE_SIZE):
                error_response = UploadErrorResponse(error="File size exceeds 10MB limit")
                return JSONResponse(
                    status_code=400,
                    content=error_response.dict()
                )
            
            await file.seek(0)
            
            file_hash = await FileHashUtils.generate_file_hash(file)
            
            db_service = DBService(db)
            duplicate_check = db_service.check_duplicate_file_by_hash(file_hash, user.get("user_id"))
            
            if duplicate_check.is_duplicate:
                error_response = UploadErrorResponse(
                    error=f"Duplicate file detected. This file was already uploaded as '{duplicate_check.existing_filename}'"
                )
                return JSONResponse(
                    status_code=409,
                    content=error_response.dict()
                )
            
            await file.seek(0)
            
            file_processor = FileProcessor(db_service, user.get("user_id"))
            
            upload_result = await file_processor.upload_file_with_hash(
                file=file,
                file_hash=file_hash
            )

            text_content = None
            if is_pdf:
                text_content = file_processor.extract_text(upload_result["file_data"])
            
            manual_upload = file_processor._create_manual_upload_entry(
                user_id=user.get("user_id"),
                document_type=document_type.upper(),
                upload_notes=upload_notes
            )
            
            source = file_processor._get_source_from_manual_upload(manual_upload.id)
            
            attachment = file_processor._create_attachment_entry(
                source_id=source.id,
                user_id=user.get("user_id"),
                filename=upload_result["filename"],
                file_data=upload_result["file_data"],
                s3_key=upload_result["s3_key"],
                file_hash=upload_result["file_hash"],
                mime_type=upload_result["mime_type"],
                extracted_text=text_content
            )
            
            db_service.commit()
            
            # Delegate all processing to DocumentProcessor
            document_processor = DocumentProcessor(db_service, user.get("user_id"))
            
            ocr_success, processing_results, processing_method = await document_processor.process_document(
                file_data=upload_result["file_data"],
                filename=upload_result["filename"],
                source_id=source.id,
                document_type=document_type,
                text_content=text_content,
                s3_key=upload_result["s3_key"],
                upload_notes=upload_notes,
                file_hash=upload_result["file_hash"]
            )
            
            success_data = UploadSuccessData(
                success=True,
                attachment_id=attachment.id,
                manual_upload_id=manual_upload.id,
                filename=upload_result["filename"],
                s3_key=upload_result["s3_key"],
                file_size=upload_result["file_size"],
                document_type=document_type
            )
            
            
            success_response = UploadSuccessResponse(
                message=f"File uploaded successfully",
                data=success_data
            )
            
            return JSONResponse(
                status_code=200,
                content=success_response.dict()
            )
            
        except Exception as e:
            error_response = UploadErrorResponse(error=f"Upload failed: {str(e)}")
            return JSONResponse(
                status_code=500, 
                content=error_response.dict()
            )

    @staticmethod
    async def get_attachment_signed_url(s3_url: str, db):
        try:
            s3 = S3Service()
            signed_url = await s3.get_presigned_url(s3_url)

            return {
                "url": signed_url
            } 

        except NotFoundError:
            raise
        except Exception as e:
            raise ExternalServiceError("S3", f"Failed to generate signed URL: {str(e)}")
