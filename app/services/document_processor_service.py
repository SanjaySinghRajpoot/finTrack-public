import base64
import logging
import os
import tempfile
from typing import Optional, List, Tuple

from app.services.db_service import DBService
from app.services.document_staging_service import DocumentStagingStatusManager
from app.services.file_service import FileService, ProcessingError


class DocumentProcessor:
    """Handles document processing with LLM and OCR integration."""
    
    def __init__(self, db_service: DBService, user_id: int):
        self.db_service = db_service
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        self.DEFAULT_MIME_TYPE = "application/pdf"
        self.status_manager = DocumentStagingStatusManager(db_service, self.logger)
        self.file_service = FileService()
        
    async def process_with_ocr(
        self, 
        file_data: bytes, 
        filename: str, 
        source_id: int, 
        document_type: str
    ) -> Optional[dict]:
        """Process document using OCR service."""
        temp_file_path = None
        try:
            from app.services.ocr import OCRService
            
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
        """Process PDF document with LLM service."""
        try:
            from app.services.llm_service import LLMService, DocumentProcessingRequest
            
            # Pass DBService instance, not database session
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
            
            results = await llm_service.llm_manual_processing([processing_request])
            self.logger.info(f"LLM PDF processing completed with {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"LLM PDF processing failed: {e}")
            # Re-raise the exception to fail the file processing
            raise Exception(f"LLM PDF processing failed for {filename}: {str(e)}")
    
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
        """Process image document with LLM service."""
        try:
            from app.services.llm_service import LLMService, DocumentProcessingRequest
            
            # Pass DBService instance, not database session
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
            
            results = await llm_service.llm_image_processing_batch([processing_request])
            self.logger.info(f"LLM image processing completed with {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"LLM image processing failed: {e}")
            # Re-raise the exception to fail the file processing
            raise Exception(f"LLM image processing failed for {filename}: {str(e)}")
    
    async def process_html_content_with_llm(
        self,
        html_content: str,
        source_id: int,
        email_subject: str,
        email_from: str,
        upload_notes: Optional[str] = None
    ) -> List[dict]:
        """Process HTML/email content with LLM service."""
        try:
            from app.services.llm_service import LLMService
            
            # Pass DBService instance, not database session
            llm_service = LLMService(self.user_id, self.db_service)
            
            email_payload = {
                "source_id": source_id,
                "user_id": self.user_id,
                "from": email_from,
                "subject": email_subject,
                "body": html_content,
                "attachments": [],
                "has_attachments": False
            }
            
            results = await llm_service.llm_batch_processing([email_payload])
            self.logger.info(f"LLM HTML content processing completed with {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"LLM HTML content processing failed: {e}")
            # Re-raise the exception to fail the file processing
            raise Exception(f"LLM HTML content processing failed: {str(e)}")
    
    async def process_document(self, **kwargs) -> Tuple[bool, List[dict], str]:
        """Process document with centralized status management. Handles files (PDF/images) and HTML/text email content."""
        source_id = kwargs.get('source_id')
        document_type = kwargs.get('document_type')
        
        if not source_id or not document_type:
            raise ValueError("source_id and document_type are required parameters")
        
        filename = kwargs.get('filename')
        file_data = kwargs.get('file_data')
        text_content = kwargs.get('text_content')
        html_content = kwargs.get('html_content')
        email_subject = kwargs.get('email_subject')
        email_from = kwargs.get('email_from')
        s3_key = kwargs.get('s3_key')
        upload_notes = kwargs.get('upload_notes')
        file_hash = kwargs.get('file_hash')
        
        ocr_success = False
        processing_results = []
        processing_method = "none"
        
        try:
            self.status_manager.update_status_in_progress(source_id)
            
            # Process email HTML/text content
            if html_content and email_subject:
                self.logger.info(f"Processing email content from {email_from} (source_id: {source_id})")
                processing_results = await self.process_html_content_with_llm(
                    html_content=html_content,
                    source_id=source_id,
                    email_subject=email_subject,
                    email_from=email_from or "unknown",
                    upload_notes=upload_notes
                )
                processing_method = "llm_email_content"
            
            # Process file (PDF/image)
            elif filename and file_data:
                self.logger.info(f"Processing file {filename} (source_id: {source_id})")
                
                if self.file_service.is_pdf(filename) and text_content:
                    processing_results = await self.process_pdf_with_llm(
                        text_content=text_content,
                        source_id=source_id,
                        filename=filename,
                        s3_key=s3_key or "",
                        upload_notes=upload_notes,
                        file_hash=file_hash
                    )
                    processing_method = "llm_pdf"
                    
                elif self.file_service.is_image(filename):
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
            else:
                raise ProcessingError("Invalid processing parameters: must provide either html_content or file_data")
            
            if processing_results:
                self.status_manager.update_status_completed(
                    source_id=source_id,
                    processing_method=processing_method,
                    results_count=len(processing_results),
                    ocr_success=ocr_success
                )
            
            return ocr_success, processing_results, processing_method
            
        except Exception as e:
            self.status_manager.update_status_failed(
                source_id=source_id,
                error=e,
                filename=filename or f"email_{email_subject}" if email_subject else "unknown"
            )
            raise e
