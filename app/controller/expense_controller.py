from app.models.models import Expense
from app.services.db_service import DBService
from app.models.scheme import ExpenseCreate, ExpenseUpdate
from app.utils.exceptions import NotFoundError, DatabaseError


class ExpenseController:
    @staticmethod
    async def create_expense(payload: ExpenseCreate, user, db):
        try:
            db_service = DBService(db)
            expense = Expense(
                user_id=user.get("user_id"),
                amount=payload.amount,
                currency=payload.currency,
                category=payload.category,
                description=payload.description
            )

            if payload.is_import:
                # Get the processed data to extract source_id
                processed_data = db_service.get_processed_data_by_id(payload.processed_data_id)
                if (processed_data):
                    expense.source_id = processed_data.source_id
                
                db_service.import_processed_data(payload.processed_data_id)

            return db_service.create_expense(expense)
        except Exception as e:
            raise DatabaseError(f"Failed to create expense: {str(e)}")

    @staticmethod
    async def list_expenses(user, db, limit: int, offset: int):
        try:
            db_service = DBService(db)
            return db_service.list_expenses(user.get("user_id"), limit, offset)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve expenses: {str(e)}")

    @staticmethod
    async def get_expense(expense_uuid: str, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_uuid, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_uuid))
            return expense
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve expense: {str(e)}")

    @staticmethod
    async def update_expense(expense_uuid: str, payload: ExpenseUpdate, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_uuid, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_uuid))

            return db_service.update_expense(expense, payload.to_dict())
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update expense: {str(e)}")

    @staticmethod
    async def delete_expense(expense_uuid: str, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_uuid, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_uuid))
            return db_service.soft_delete_expense(expense)
        except NotFoundError:
            raise
        except DatabaseError:
            # Re-raise database errors as they already have clean messages
            raise
        except Exception as e:
            raise DatabaseError("Failed to delete expense")
