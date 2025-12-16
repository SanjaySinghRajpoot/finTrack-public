"""Email Repository Module"""

from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.models import Email
from app.repositories.base_repository import BaseRepository


class EmailRepository(BaseRepository[Email]):

    def __init__(self, db_session: Session):
        super().__init__(db_session, Email)

    def get_by_gmail_message_id(self, gmail_message_id: str) -> Optional[Email]:
        return self.db.query(Email).filter_by(gmail_message_id=gmail_message_id).first()

    def get_by_source_id(self, source_id: int) -> Optional[Email]:
        return self.db.query(Email).filter_by(source_id=source_id).first()

    def get_unprocessed(self) -> List[Email]:
        return self.db.query(Email).filter_by(is_processed=False).all()

    def mark_as_processed(self, email_ids: List[int]) -> None:
        if not email_ids:
            return

        try:
            query = text("""
                UPDATE emails
                SET is_processed = TRUE
                WHERE id = ANY(:email_ids)
            """)
            self.db.execute(query, {"email_ids": email_ids})
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_user_id(self, user_id: int, limit: int = 50) -> List[Email]:
        return (
            self.db.query(Email)
            .filter(Email.user_id == user_id)
            .order_by(Email.created_at.desc())
            .limit(limit)
            .all()
        )
