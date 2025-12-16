"""User Repository Module"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session, defer

from app.models.models import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):

    def __init__(self, db_session: Session):
        super().__init__(db_session, User)

    def get_by_id(self, user_id: int) -> Optional[User]:
        return (
            self.db.query(User)
            .options(defer(User.password))
            .filter(User.id == user_id)
            .first()
        )

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def update_details(self, user_id: int, updated_details: dict) -> Optional[User]:
        try:
            user = self.get_by_id(user_id)
            if user is None:
                return None

            for key, value in updated_details.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            raise e
