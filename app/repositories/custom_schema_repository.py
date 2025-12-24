"""Custom Schema Repository Module"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.models import CustomSchema
from app.repositories.base_repository import BaseRepository


class CustomSchemaRepository(BaseRepository[CustomSchema]):
    """Repository for CustomSchema database operations"""

    def __init__(self, db_session: Session):
        super().__init__(db_session, CustomSchema)

    def get_by_user_id(self, user_id: int) -> Optional[CustomSchema]:
        """Get custom schema for a specific user"""
        return (
            self.db.query(CustomSchema)
            .filter(CustomSchema.user_id == user_id)
            .first()
        )

    def create_or_update(self, user_id: int, data: Dict[str, Any]) -> CustomSchema:
        """Create or update custom schema for a user"""
        existing = self.get_by_user_id(user_id)
        
        if existing:
            # Update existing schema
            for key, value in data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new schema
            schema = CustomSchema(user_id=user_id, **data)
            self.db.add(schema)
            self.db.commit()
            self.db.refresh(schema)
            return schema

    def delete_by_user_id(self, user_id: int) -> bool:
        """Delete custom schema for a user"""
        schema = self.get_by_user_id(user_id)
        if schema:
            self.db.delete(schema)
            self.db.commit()
            return True
        return False

    def update_fields(self, user_id: int, fields: List[Dict[str, Any]]) -> Optional[CustomSchema]:
        """Update only the fields of a custom schema"""
        schema = self.get_by_user_id(user_id)
        if schema:
            schema.fields = fields
            self.db.commit()
            self.db.refresh(schema)
            return schema
        return None
