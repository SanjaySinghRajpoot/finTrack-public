import types
from datetime import datetime, timedelta
from typing import List

from requests import Session
from sqlalchemy import text
from sqlalchemy.orm import defer, joinedload, selectinload

from app.models.models import Attachment, Email, ProcessedEmailData, UserToken, Expense, User, IntegrationStatus, \
    EmailConfig, IntegrationState, Subscription, Feature, Plan, PlanFeature, Integration, IntegrationFeature
from app.utils.utils import DuplicateCheckResult

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

    def flush(self):
        try:
            self.db.flush()
        except Exception as e:
            self.db.rollback()
            raise e

    def commit(self):
        """Simple commit wrapper with rollback on error."""
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def update(self, obj):
        try:
            # self.db.merge(obj)  # merges state of 'obj' into the current session
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as e:
            self.db.rollback()  # rollback to maintain DB integrity
            raise e

    def get_attachment_by_id(self, attachment_id: str):
        return self.db.query(Attachment).filter_by(id=attachment_id).first()

    def save_attachment(self, attachment: Attachment):
        self.add(attachment)

    def save_proccessed_email_data(self, processed_email_data: ProcessedEmailData):

        existing = (
            self.db.query(ProcessedEmailData)
            .filter_by(source_id=processed_email_data.source_id)
            .first()
        )

        # If not found, add it to the DB
        if not existing:
            self.add(processed_email_data)

    def get_not_processed_mails(self) -> List[Email]:
        try:
            return self.db.query(Email).filter_by(is_processed=False).all()
        except Exception as e:
            raise e

    def update_email_status(self, email_ids: list[int]):
        try:
            if not email_ids:
                return

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

    def get_processed_data(self, user_id: int, limit: int, offset: int):
        try:
            # Query ProcessedEmailData with eager loading of related data
            query = (
                self.db.query(ProcessedEmailData)
                .filter(
                    ProcessedEmailData.user_id == user_id,
                    ProcessedEmailData.is_imported == False
                )
                .options(
                    # Eager load processed items
                    selectinload(ProcessedEmailData.processed_items),
                    # Eager load attachment relationship
                    joinedload(ProcessedEmailData.attachment),
                    # Eager load source for additional context
                    joinedload(ProcessedEmailData.source)
                )
                .offset(offset)
                .limit(limit)
            )

            results = query.all()

            # Total count for pagination metadata
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

    def get_email_by_pk(self, email_id: int):
        """Get email by primary key ID"""
        return self.db.query(Email).filter_by(id=email_id).first()
    
    def get_email_by_source_id(self, source_id: int):
        """Get email by source_id"""
        return self.db.query(Email).filter_by(source_id=source_id).first()

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

    def get_processed_data_by_id(self, processed_data_id: int) -> ProcessedEmailData:
        """Get ProcessedEmailData by ID"""
        try:
            return (
                self.db.query(ProcessedEmailData)
                .filter(ProcessedEmailData.id == processed_data_id)
                .first()
            )
        except Exception as e:
            raise e

    # ------------------- Attachment Queries -------------

    def get_attachement_data(self, source_id) -> Attachment:
        try:
            return self.db.query(Attachment).filter(Attachment.source_id == source_id).first()
        except Exception as e:
            raise e

    def get_attachments_by_email_id(self, email_id) -> List[Attachment]:
        """Get attachments by email_id - finds source_id from email first"""
        try:
            email = self.get_email_by_pk(email_id)
            if not email or not email.source_id:
                return []
            return self.db.query(Attachment).filter(Attachment.source_id == email.source_id).all()
        except Exception as e:
            raise e

    def check_duplicate_file_by_hash(self, file_hash: str, user_id: int = None) -> 'DuplicateCheckResult':
        """
        Check if a file with the given hash already exists in the database.
        
        Args:
            file_hash: SHA-256 hash of the file
            user_id: Optional user ID to check for user-specific duplicates
            
        Returns:
            DuplicateCheckResult: Result object indicating if duplicate exists
        """
        try:

            query = self.db.query(Attachment).filter(Attachment.file_hash == file_hash, Attachment.user_id == user_id)

            existing_attachment = query.first()
            
            if existing_attachment:
                return DuplicateCheckResult(
                    is_duplicate=True,
                    existing_attachment_id=existing_attachment.id,
                    existing_filename=existing_attachment.filename,
                    existing_source_id=existing_attachment.source_id
                )
            else:
                return DuplicateCheckResult(is_duplicate=False)
                
        except Exception as e:
            raise e

    def get_attachment_by_hash(self, file_hash: str) -> Attachment:
        """Get attachment by file hash"""
        try:
            return self.db.query(Attachment).filter(Attachment.file_hash == file_hash).first()
        except Exception as e:
            raise e

    def save_attachment_with_hash(self, attachment: Attachment, file_hash: str):
        """Save attachment with file hash"""
        try:
            attachment.file_hash = file_hash
            self.add(attachment)
            return attachment
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

    def update_user_details(self, user_id, updated_details):
        try:
            user = self.get_user_by_id(user_id)
            if user is None:
                return

            for key, value in updated_details.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)

        except Exception as e:
            raise e

    # ------------------- Subscription & Feature Queries ---------------------
    def get_user_subscription(self, user_id: int):
        """
        Get the active subscription for a user along with plan details.
        """
        try:
            return (
                self.db.query(Subscription)
                .options(joinedload(Subscription.plan))
                .filter(
                    Subscription.user_id == user_id,
                    Subscription.status.in_(['active', 'trial'])
                )
                .order_by(Subscription.created_at.desc())
                .first()
            )
        except Exception as e:
            raise e

    def get_all_features(self):
        """
        Get all active features with their credit costs.
        """
        try:
            return (
                self.db.query(Feature)
                .filter(Feature.is_active == True)
                .all()
            )
        except Exception as e:
            raise e

    def get_plan_features(self, plan_id: int):
        """
        Get all features enabled for a specific plan.
        """
        try:
            return (
                self.db.query(PlanFeature, Feature)
                .join(Feature, PlanFeature.feature_id == Feature.id)
                .filter(
                    PlanFeature.plan_id == plan_id,
                    PlanFeature.is_enabled == True,
                    Feature.is_active == True
                )
                .all()
            )
        except Exception as e:
            raise e

    def can_use_feature(self, user_id: int, feature_key: str):
        """
        Check if a user can use a specific feature based on their subscription credits
        and plan permissions.
        """
        try:
            # Get user's active subscription
            subscription = self.get_user_subscription(user_id)
            if not subscription:
                return False, "No active subscription found"

            # Get the feature details
            feature = (
                self.db.query(Feature)
                .filter(
                    Feature.feature_key == feature_key,
                    Feature.is_active == True
                )
                .first()
            )
            
            if not feature:
                return False, "Feature not found"

            # Check if feature is enabled in user's plan
            plan_feature = (
                self.db.query(PlanFeature)
                .filter(
                    PlanFeature.plan_id == subscription.plan_id,
                    PlanFeature.feature_id == feature.id,
                    PlanFeature.is_enabled == True
                )
                .first()
            )

            if not plan_feature:
                return False, "Feature not available in current plan"

            # Get the credit cost (use custom cost if set, otherwise default)
            credit_cost = plan_feature.custom_credit_cost or feature.credit_cost

            # Check if user has enough credits
            if subscription.credit_balance >= credit_cost:
                return True, "Feature available"
            else:
                return False, f"Insufficient credits. Required: {credit_cost}, Available: {subscription.credit_balance}"

        except Exception as e:
            raise e

    def get_feature_by_key(self, feature_key: str):
        """
        Get feature by its key.
        """
        try:
            return (
                self.db.query(Feature)
                .filter(
                    Feature.feature_key == feature_key,
                    Feature.is_active == True
                )
                .first()
            )
        except Exception as e:
            raise e

    # ------------------- Processed Items Management ---------------------
    def save_processed_items(self, processed_email_id: int, items_data: list):
        """Save processed items for a given processed_email_data record"""
        try:
            from app.models.models import ProcessedItem
            
            if not items_data:
                return
                
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

    # ------------------- Integration Management Queries ---------------------
    def get_integration_by_slug(self, slug: str):
        """
        Get integration master record by slug.
        """
        try:
            return (
                self.db.query(Integration)
                .filter(
                    Integration.slug == slug,
                    Integration.is_active == True
                )
                .first()
            )
        except Exception as e:
            raise e

    def get_integration_features(self, integration_id: int):
        """
        Get all features linked to an integration.
        """
        try:
            return (
                self.db.query(IntegrationFeature, Feature)
                .join(Feature, IntegrationFeature.feature_id == Feature.id)
                .filter(
                    IntegrationFeature.integration_id == integration_id,
                    IntegrationFeature.is_enabled == True,
                    Feature.is_active == True
                )
                .order_by(IntegrationFeature.execution_order.nullslast())
                .all()
            )
        except Exception as e:
            raise e

    def link_user_integration_to_master(self, user_integration_id: str, integration_master_id: int):
        """
        Link a user's integration status to the master integration record.
        """
        try:
            user_integration = (
                self.db.query(IntegrationStatus)
                .filter(IntegrationStatus.id == user_integration_id)
                .first()
            )
            
            if user_integration:
                user_integration.integration_master_id = integration_master_id
                self.db.commit()
                return user_integration
            
            return None
        except Exception as e:
            self.db.rollback()
            raise e
