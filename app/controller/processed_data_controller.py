from app.services.db_service import DBService
from app.models.scheme import (
    StagingDocumentsResponse,
    StagingDocumentData,
    StagingDocumentSource,
    StagingDocumentsPagination
)
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class ProcessedDataController:
    @staticmethod
    async def get_payment_info(user, db, limit: int, offset: int):
        user_id = user.get("user_id")
        db_service = DBService(db)
        return db_service.get_processed_data(user_id=user_id, limit=limit, offset=offset)

    @staticmethod
    async def get_staging_documents(
        user, 
        db, 
        limit: int, 
        offset: int, 
        status: str = None
    ) -> StagingDocumentsResponse:
        """
        Get paginated staging documents for the authenticated user.
        
        Args:
            user: Authenticated user from JWT
            db: Database session
            limit: Number of records per page
            offset: Number of records to skip
            status: Optional filter by processing status (pending, in_progress, completed, failed)
        
        Returns:
            StagingDocumentsResponse with paginated list of staging documents
        
        Raises:
            HTTPException: If there's an error fetching the documents
        """
        try:
            user_id = user.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="User not authenticated")
            
            db_service = DBService(db)
            result = db_service.get_staging_documents(
                user_id=user_id, 
                limit=limit, 
                offset=offset,
                status_filter=status
            )
            
            # Transform the staging documents to Pydantic models
            staging_docs = []
            for doc in result.get("data", []):
                try:
                    source_data = None
                    if doc.source:
                        source_data = StagingDocumentSource(
                            id=doc.source.id,
                            type=doc.source.type,
                            external_id=doc.source.external_id,
                            created_at=doc.source.created_at.isoformat() if doc.source.created_at else None
                        )
                    
                    staging_doc = StagingDocumentData(
                        id=doc.id,
                        uuid=str(doc.uuid),
                        filename=doc.filename,
                        file_hash=doc.file_hash,
                        s3_key=doc.s3_key,
                        mime_type=doc.mime_type,
                        file_size=doc.file_size,
                        document_type=doc.document_type,
                        source_type=doc.source_type,
                        upload_notes=doc.upload_notes,
                        processing_status=doc.document_processing_status,
                        processing_attempts=doc.processing_attempts,
                        max_attempts=doc.max_attempts,
                        error_message=doc.error_message,
                        meta_data=doc.meta_data,
                        priority=doc.priority,
                        created_at=doc.created_at.isoformat() if doc.created_at else None,
                        updated_at=doc.updated_at.isoformat() if doc.updated_at else None,
                        processing_started_at=doc.processing_started_at.isoformat() if doc.processing_started_at else None,
                        processing_completed_at=doc.processing_completed_at.isoformat() if doc.processing_completed_at else None,
                        source=source_data
                    )
                    staging_docs.append(staging_doc)
                except Exception as doc_error:
                    logger.warning(f"Error processing staging document {doc.id}: {str(doc_error)}")
                    continue
            
            pagination = result.get("pagination", {})
            
            return StagingDocumentsResponse(
                data=staging_docs,
                pagination=StagingDocumentsPagination(
                    total=pagination.get("total", 0),
                    limit=pagination.get("limit", limit),
                    offset=pagination.get("offset", offset),
                    has_more=pagination.get("has_more", False)
                )
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching staging documents: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to fetch staging documents: {str(e)}"
            )
