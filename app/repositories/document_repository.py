"""Document Repository Module"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.models import ProcessedEmailData, ProcessedItem, DocumentStaging
from app.repositories.base_repository import BaseRepository


class DocumentRepository(BaseRepository[ProcessedEmailData]):

    def __init__(self, db_session: Session):
        super().__init__(db_session, ProcessedEmailData)

    def save_processed_data(self, processed_data: ProcessedEmailData) -> Optional[ProcessedEmailData]:
        existing = (
            self.db.query(ProcessedEmailData)
            .filter_by(source_id=processed_data.source_id)
            .first()
        )

        if not existing:
            return self.add(processed_data)
        return None

    def get_paginated_for_user(self, user_id: int, limit: int, offset: int) -> Dict[str, Any]:
        query = (
            self.db.query(ProcessedEmailData)
            .filter(
                ProcessedEmailData.user_id == user_id,
                ProcessedEmailData.is_imported == False
            )
            .options(
                selectinload(ProcessedEmailData.processed_items),
                joinedload(ProcessedEmailData.attachment),
                joinedload(ProcessedEmailData.source)
            )
            .offset(offset)
            .limit(limit)
        )

        results = query.all()

        total_count = (
            self.db.query(ProcessedEmailData)
            .filter(
                ProcessedEmailData.user_id == user_id,
                ProcessedEmailData.is_imported == False
            )
            .count()
        )

        return {
            "data": results,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        }

    def mark_as_imported(self, processed_data_id: int) -> None:
        try:
            data = self.get_by_id(processed_data_id)

            if not data:
                raise ValueError(f"Processed data with ID {processed_data_id} not found")

            data.is_imported = True
            data.updated_at = datetime.utcnow()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def save_processed_items(self, processed_email_id: int, items_data: list) -> None:
        if not items_data:
            return
            
        try:
            for item_data in items_data:
                processed_item = ProcessedItem(
                    processed_email_id=processed_email_id,
                    item_name=item_data.get("item_name"),
                    item_code=item_data.get("item_code"),
                    category=item_data.get("category"),
                    quantity=item_data.get("quantity", 1.0),
                    unit=item_data.get("unit"),
                    rate=item_data.get("rate"),
                    discount=item_data.get("discount", 0.0),
                    tax_percent=item_data.get("tax_percent"),
                    total_amount=item_data.get("total_amount"),
                    currency=item_data.get("currency", "INR"),
                    meta_data=item_data.get("meta_data")
                )
                self.db.add(processed_item)
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def get_pending_staged_documents(self, limit: int = 10) -> List[DocumentStaging]:
        return (
            self.db.query(DocumentStaging)
            .filter(DocumentStaging.document_processing_status == "pending")
            .order_by(
                DocumentStaging.priority.desc(),
                DocumentStaging.created_at.asc()
            )
            .limit(limit)
            .all()
        )

    def update_staging_status(
        self,
        staging_id: int,
        status: str,
        error_message: str = None,
        attempts: int = None,
        metadata: dict = None
    ) -> Optional[DocumentStaging]:
        try:
            staging = (
                self.db.query(DocumentStaging)
                .filter(DocumentStaging.id == staging_id)
                .first()
            )
            
            if not staging:
                raise ValueError(f"DocumentStaging with ID {staging_id} not found")
            
            staging.document_processing_status = status.lower()
            
            if status.lower() == "in_progress":
                staging.processing_started_at = datetime.utcnow()
            elif status.lower() in ["completed", "failed"]:
                staging.processing_completed_at = datetime.utcnow()
            
            if attempts is not None:
                staging.processing_attempts = attempts
            
            if error_message:
                staging.error_message = error_message
            
            if metadata:
                if staging.meta_data:
                    staging.meta_data.update(metadata)
                else:
                    staging.meta_data = metadata
            
            self.db.commit()
            return staging
            
        except Exception as e:
            self.db.rollback()
            raise e

    def get_paginated_staging_documents(
        self, 
        user_id: int, 
        limit: int, 
        offset: int,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get paginated staging documents for a user.
        
        Args:
            user_id: The user's ID
            limit: Number of records to return
            offset: Number of records to skip
            status_filter: Optional filter by processing status (pending, in_progress, completed, failed)
        
        Returns:
            Dict with data and pagination info
        """
        query = (
            self.db.query(DocumentStaging)
            .filter(DocumentStaging.user_id == user_id)
            .options(joinedload(DocumentStaging.source))
        )
        
        # Apply status filter if provided
        if status_filter:
            query = query.filter(
                DocumentStaging.document_processing_status == status_filter.lower()
            )
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply ordering and pagination
        results = (
            query
            .order_by(
                DocumentStaging.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        return {
            "data": results,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        }
