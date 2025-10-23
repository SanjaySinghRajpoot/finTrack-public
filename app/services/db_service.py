import types
from datetime import datetime, timedelta
from typing import List

from requests import Session
from sqlalchemy.orm import defer, joinedload

from app.models.models import Attachment, Email, ProcessedEmailData, UserToken, Expense, User, IntegrationStatus, \
    EmailConfig, IntegrationState


class DBService:
    def __init__(self, db_session: Session):
        if isinstance(db_session, types.GeneratorType):
            db_session = next(db_session)
        self.db: Session = db_session

    def add(self, obj):
        try:
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as e:
            raise e

    def get_attachment_by_id(self, attachment_id: str):
        return self.db.query(Attachment).filter_by(attachment_id=attachment_id).first()

    def save_attachment(self, attachment: Attachment):
        self.add(attachment)

    def save_proccessed_email_data(self, processed_email_data: ProcessedEmailData):
        self.add(processed_email_data)

    def get_processed_data(self, user_id: int, limit: int, offset: int):
        try:
            # here we need to add another query to get attachment info and file url
            query = (
                self.db.query(ProcessedEmailData)
                .filter(
                    ProcessedEmailData.user_id == user_id,
                    ProcessedEmailData.is_imported == False
                )
                .offset(offset)
                .limit(limit)
            )

            results = query.all()

            # Optional: total count for pagination metadata
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
        except Exception as e:
            raise e


    def get_email_by_id(self, msg_id):
        return self.db.query(Email).filter_by(gmail_message_id=msg_id).first()

    def get_user_id_from_integration_status(self):
        results = (
            self.db.query(
                IntegrationStatus.user_id,
                IntegrationStatus.id
            )
            .filter(IntegrationStatus.status == IntegrationState.connected.value)
            .order_by(IntegrationStatus.created_at)
            .all()
        )
        return [(row.user_id, row.id) for row in results]

    def update_sync_data(self, integration_id: str) -> None:
        try:
            now = datetime.utcnow()

            # Fetch the integration record
            integration_status = (
                self.db.query(IntegrationStatus)
                .filter(IntegrationStatus.id == integration_id)
                .first()
            )

            if not integration_status:
                raise ValueError(f"Integration with ID {integration_id} not found")

            # Calculate next sync time and duration (example: 24 hours = 1440 minutes)
            integration_status.last_synced_at = now
            integration_status.next_sync_at = now + timedelta(minutes=integration_status.sync_interval_minutes)
            integration_status.last_sync_duration = (integration_status.sync_interval_minutes or 0) * 60
            integration_status.total_syncs = (integration_status.total_syncs or 0) + 1

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise e

    def get_expired_token_user_ids(self) -> List[int]:
        """As all the tokens will expire in 1 hour"""
        # Join EmailConfig with IntegrationStatus to get user_ids directly
        user_ids = (
            self.db.query(IntegrationStatus.user_id)
            .join(EmailConfig, IntegrationStatus.id == EmailConfig.integration_id)
            .all()
        )

        return [uid for (uid,) in user_ids]

    # ---------------------- Expense Operations -----------------------------

    def create_expense(self, expense: Expense):
        try:
            self.db.add(expense)
            self.db.commit()
            self.db.refresh(expense)
            return expense
        except Exception as e:
            self.db.rollback()
            raise e

    def list_expenses(self, user_id: int, limit: int, offset: int):
        try:
            query = (
                self.db.query(Expense)
                .filter(
                    Expense.user_id == user_id,
                    Expense.deleted_at.is_(None)
                )
                .offset(offset)
                .limit(limit)
            )

            expenses = query.all()

            # Optional: total count for pagination metadata
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
            # You can log the error here if needed
            return {"error": str(e)}


    def get_expense(self, expense_id: int, user_id: int):
        return self.db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.user_id == user_id,
            Expense.deleted_at.is_(None)
        ).first()

    def update_expense(self, expense: Expense, data: dict):
        for key, value in data.items():
            if hasattr(expense, key) and value is not None:
                setattr(expense, key, value)
        expense.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def soft_delete_expense(self, expense: Expense):
        expense.deleted_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def import_processed_data(self, processed_data_id: int):
        try:
            data = (
                self.db.query(ProcessedEmailData)
                .filter(ProcessedEmailData.id == processed_data_id)
                .first()
            )

            if not data:
                raise ValueError(f"Processed data with ID {processed_data_id} not found")

            data.is_imported = True
            data.updated_at = datetime.utcnow()  # optional

            self.add(data)
        except Exception as e:
            self.db.rollback()
            print(f"Error updating processed data: {e}")
            raise e  # Re-raise so higher layers can handle/log it

    # ------------------- Attachment Queries -------------

    def get_attachement_data(self, email_id) -> Attachment:
        try:
            return self.db.query(Attachment).filter(Attachment.email_id == email_id).first()
        except Exception as e:
            raise e


    # ------------------ User Queries ---------------------
    def get_user_by_id(self, user_id) -> User:
        try:
            return (
                self.db.query(User)
                .options(defer(User.password))  # ✅ only defer password column
                .filter(User.id == user_id)
                .first()
            )
        except Exception as e:
            raise e

    def get_user_integrations(self, user_id: int):
        """
        Fetch all integration details for a given user,
        including EmailConfig and WhatsappConfig if applicable.
        """
        try:
            return self.db.query(IntegrationStatus).options(
                    joinedload(IntegrationStatus.email_config),
                    joinedload(IntegrationStatus.whatsapp_config)
                ).filter(IntegrationStatus.user_id == user_id).all()

        except Exception as e:
            raise e

    def create_user(self, user_dict) -> User:
        try:
            pass
        except Exception as e:
            raise e
