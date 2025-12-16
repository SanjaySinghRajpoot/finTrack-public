"""
Base Repository Module - Provides common database operations for all repositories.
"""

import types
from abc import ABC
from datetime import datetime
from typing import TypeVar, Generic, Type, List, Optional, Any, Dict

from sqlalchemy.orm import Session

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository implementing common CRUD operations."""

    def __init__(self, db_session: Session, model_class: Type[T]):
        if isinstance(db_session, types.GeneratorType):
            db_session = next(db_session)
        self.db: Session = db_session
        self.model_class = model_class

    def add(self, obj: T) -> T:
        try:
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as e:
            self.db.rollback()
            raise e

    def add_without_commit(self, obj: T) -> T:
        self.db.add(obj)
        return obj

    def update(self, obj: T) -> T:
        try:
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, obj: T) -> None:
        try:
            self.db.delete(obj)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete(self, obj: T) -> T:
        try:
            obj.deleted_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, id: Any) -> Optional[T]:
        return self.db.query(self.model_class).filter_by(id=id).first()

    def get_all(self) -> List[T]:
        return self.db.query(self.model_class).all()

    def get_by_filter(self, **filters) -> List[T]:
        return self.db.query(self.model_class).filter_by(**filters).all()

    def get_one_by_filter(self, **filters) -> Optional[T]:
        return self.db.query(self.model_class).filter_by(**filters).first()

    def exists(self, **filters) -> bool:
        return self.db.query(self.model_class).filter_by(**filters).first() is not None

    def get_paginated(
        self,
        filters: Dict[str, Any] = None,
        limit: int = 10,
        offset: int = 0,
        order_by: Any = None
    ) -> Dict[str, Any]:
        query = self.db.query(self.model_class)
        
        if filters:
            query = query.filter_by(**filters)
        
        if order_by is not None:
            query = query.order_by(order_by)
        
        total_count = query.count()
        results = query.offset(offset).limit(limit).all()
        
        return {
            "data": results,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        }

    def flush(self) -> None:
        try:
            self.db.flush()
        except Exception as e:
            self.db.rollback()
            raise e

    def commit(self) -> None:
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, obj: T) -> T:
        self.db.refresh(obj)
        return obj
