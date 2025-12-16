"""Expense Repository Module"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.models import Expense, ProcessedEmailData
from app.repositories.base_repository import BaseRepository


class ExpenseRepository(BaseRepository[Expense]):

    def __init__(self, db_session: Session):
        super().__init__(db_session, Expense)

    def get_by_uuid(self, expense_uuid: str, user_id: int) -> Optional[Expense]:
        try:
            return self.db.query(Expense).filter(
                Expense.uuid == expense_uuid,
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None)
            ).first()
        except Exception as e:
            from app.utils.exceptions import DatabaseError
            raise DatabaseError("Failed to retrieve expense")

    def list_for_user(self, user_id: int, limit: int, offset: int) -> Dict[str, Any]:
        try:
            query = (
                self.db.query(Expense)
                .options(
                    joinedload(Expense.processed_data).joinedload(ProcessedEmailData.attachment),
                    joinedload(Expense.processed_data).selectinload(ProcessedEmailData.processed_items)
                )
                .filter(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None)
                )
                .offset(offset)
                .limit(limit)
            )

            expenses = query.all()

            total_count = (
                self.db.query(Expense)
                .filter(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None)
                )
                .count()
            )

            return {
                "data": expenses,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def update_expense(self, expense: Expense, data: dict) -> Expense:
        for key, value in data.items():
            if hasattr(expense, key) and value is not None:
                setattr(expense, key, value)
        expense.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def soft_delete_expense(self, expense: Expense) -> Expense:
        try:
            expense.deleted_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(expense)
            return expense
        except Exception as e:
            self.db.rollback()
            from app.utils.exceptions import DatabaseError
            raise DatabaseError("Failed to delete expense")
