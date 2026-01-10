import logging
from datetime import datetime
from typing import Optional

from app.services.db_service import DBService


class DocumentStagingStatusManager:
    """Manages document staging status updates and retry logic."""
    
    def __init__(self, db_service: DBService, logger: Optional[logging.Logger] = None):
        self.db_service = db_service
        self.logger = logger or logging.getLogger(__name__)
    
    def _get_staging_document_by_source_id(self, source_id: int):
        """Retrieve staging document by source ID."""
        return self.db_service.document_repo.get_staging_document_by_source_id(source_id)
    
    def update_status_in_progress(self, source_id: int) -> None:
        """Update staging status to IN_PROGRESS."""
        try:
            staging_doc = self._get_staging_document_by_source_id(source_id)
            if staging_doc:
                self.db_service.update_staging_status(
                    staging_id=staging_doc.id,
                    status="IN_PROGRESS"
                )
                self.logger.info(f"Status updated to IN_PROGRESS for source_id: {source_id}")
        except Exception as e:
            self.logger.error(f"Failed to update status to IN_PROGRESS for source_id {source_id}: {e}")
    
    def update_status_completed(
        self, 
        source_id: int, 
        processing_method: str,
        results_count: int,
        ocr_success: bool = False
    ) -> None:
        """Update staging status to COMPLETED with metadata."""
        try:
            staging_doc = self._get_staging_document_by_source_id(source_id)
            if staging_doc:
                self.db_service.update_staging_status(
                    staging_id=staging_doc.id,
                    status="COMPLETED",
                    metadata={
                        "processing_method": processing_method,
                        "ocr_success": ocr_success,
                        "results_count": results_count
                    }
                )
                self.logger.info(
                    f"✅ Status updated to COMPLETED for source_id: {source_id} "
                    f"using {processing_method}"
                )
        except Exception as e:
            self.logger.error(f"Failed to update status to COMPLETED for source_id {source_id}: {e}")
    
    def update_status_failed(
        self, 
        source_id: int, 
        error: Exception,
        filename: str = "unknown"
    ) -> None:
        """Update staging status to FAILED or PENDING based on retry attempts."""
        try:
            staging_doc = self._get_staging_document_by_source_id(source_id)
            if not staging_doc:
                self.logger.warning(f"No staging document found for source_id {source_id}")
                return
            
            # Increment attempts and determine status based on max_attempts threshold
            new_attempts = staging_doc.processing_attempts + 1
            status = "FAILED" if new_attempts >= staging_doc.max_attempts else "PENDING"
            
            error_type = type(error).__name__
            error_message = f"{error_type}: {str(error)}"
            
            self.db_service.update_staging_status(
                staging_id=staging_doc.id,
                status=status,
                error_message=error_message,
                attempts=new_attempts,
                metadata={
                    "error_type": error_type,
                    "failed_at_attempt": new_attempts,
                    "last_error_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            if status == "FAILED":
                self.logger.warning(
                    f"⚠️ Document {filename} marked as FAILED after {new_attempts} attempts. "
                    f"Source ID: {source_id}, Error: {error_message}"
                )
            else:
                self.logger.info(
                    f"🔄 Document {filename} will be retried. "
                    f"Attempt {new_attempts}/{staging_doc.max_attempts}. Source ID: {source_id}"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update status to FAILED for source_id {source_id}: {e}")
