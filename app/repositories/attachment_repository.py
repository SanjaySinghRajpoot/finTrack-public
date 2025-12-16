"""Attachment Repository Module"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.models import Attachment, Source
from app.repositories.base_repository import BaseRepository
from app.utils.utils import DuplicateCheckResult


class AttachmentRepository(BaseRepository[Attachment]):

    def __init__(self, db_session: Session):
        super().__init__(db_session, Attachment)

    def get_by_source_id(self, source_id: int) -> Optional[Attachment]:
        return self.db.query(Attachment).filter(Attachment.source_id == source_id).first()

    def get_all_by_source_id(self, source_id: int) -> List[Attachment]:
        return self.db.query(Attachment).filter(Attachment.source_id == source_id).all()

    def get_by_file_hash(self, file_hash: str) -> Optional[Attachment]:
        return self.db.query(Attachment).filter(Attachment.file_hash == file_hash).first()

    def check_duplicate_by_hash(self, file_hash: str, user_id: int = None) -> DuplicateCheckResult:
        try:
            query = self.db.query(Attachment).filter(
                Attachment.file_hash == file_hash,
                Attachment.user_id == user_id
            )

            existing_attachment = query.first()
            
            if existing_attachment:
                manual_upload_id = None
                if existing_attachment.source_id:
                    source = self.db.query(Source).filter(Source.id == existing_attachment.source_id).first()
                    if source and source.type == "manual" and source.external_id:
                        try:
                            manual_upload_id = int(source.external_id)
                        except (ValueError, TypeError):
                            pass
                
                return DuplicateCheckResult(
                    is_duplicate=True,
                    attachment_id=existing_attachment.id,
                    existing_attachment_id=existing_attachment.id,
                    existing_filename=existing_attachment.filename,
                    existing_source_id=existing_attachment.source_id,
                    manual_upload_id=manual_upload_id
                )
            else:
                return DuplicateCheckResult(is_duplicate=False)
                
        except Exception as e:
            raise e

    def save_with_hash(self, attachment: Attachment, file_hash: str) -> Attachment:
        attachment.file_hash = file_hash
        return self.add(attachment)

    def update_extracted_text(self, attachment_id: int, extracted_text: str) -> Optional[Attachment]:
        try:
            attachment = self.get_by_id(attachment_id)
            
            if attachment:
                attachment.extracted_text = extracted_text
                self.db.commit()
                return attachment
            
            return None
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_user_id(self, user_id: int, limit: int = 50) -> List[Attachment]:
        return (
            self.db.query(Attachment)
            .filter(Attachment.user_id == user_id)
            .order_by(Attachment.created_at.desc())
            .limit(limit)
            .all()
        )
