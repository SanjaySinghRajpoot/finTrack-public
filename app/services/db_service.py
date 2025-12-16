"""
DB Service Module - Facade for backward-compatible database operations.
Delegates to specialized repositories internally.
"""

import types
from typing import List, Optional, Tuple, Any, Dict

from sqlalchemy.orm import Session

from app.models.models import (
    Attachment, Email, ProcessedEmailData, Expense, User, 
    IntegrationStatus, Feature, Integration, IntegrationFeature
)
from app.utils.utils import DuplicateCheckResult
from app.repositories import (
    EmailRepository,
    AttachmentRepository,
    UserRepository,
    ExpenseRepository,
    IntegrationRepository,
    SubscriptionRepository,
    DocumentRepository,
)


class DBService:

    def __init__(self, db_session: Session):
        if isinstance(db_session, types.GeneratorType):
            db_session = next(db_session)
        self.db: Session = db_session
        
        self._email_repo: Optional[EmailRepository] = None
        self._attachment_repo: Optional[AttachmentRepository] = None
        self._user_repo: Optional[UserRepository] = None
        self._expense_repo: Optional[ExpenseRepository] = None
        self._integration_repo: Optional[IntegrationRepository] = None
        self._subscription_repo: Optional[SubscriptionRepository] = None
        self._document_repo: Optional[DocumentRepository] = None

    @property
    def email_repo(self) -> EmailRepository:
        if self._email_repo is None:
            self._email_repo = EmailRepository(self.db)
        return self._email_repo

    @property
    def attachment_repo(self) -> AttachmentRepository:
        if self._attachment_repo is None:
            self._attachment_repo = AttachmentRepository(self.db)
        return self._attachment_repo

    @property
    def user_repo(self) -> UserRepository:
        if self._user_repo is None:
            self._user_repo = UserRepository(self.db)
        return self._user_repo

    @property
    def expense_repo(self) -> ExpenseRepository:
        if self._expense_repo is None:
            self._expense_repo = ExpenseRepository(self.db)
        return self._expense_repo

    @property
    def integration_repo(self) -> IntegrationRepository:
        if self._integration_repo is None:
            self._integration_repo = IntegrationRepository(self.db)
        return self._integration_repo

    @property
    def subscription_repo(self) -> SubscriptionRepository:
        if self._subscription_repo is None:
            self._subscription_repo = SubscriptionRepository(self.db)
        return self._subscription_repo

    @property
    def document_repo(self) -> DocumentRepository:
        if self._document_repo is None:
            self._document_repo = DocumentRepository(self.db)
        return self._document_repo

    def add(self, obj):
        try:
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as e:
            self.db.rollback()
            raise e

    def flush(self):
        try:
            self.db.flush()
        except Exception as e:
            self.db.rollback()
            raise e

    def commit(self):
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def update(self, obj):
        try:
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as e:
            self.db.rollback()
            raise e

    def get_email_by_id(self, msg_id) -> Optional[Email]:
        return self.email_repo.get_by_gmail_message_id(msg_id)

    def get_email_by_pk(self, email_id: int) -> Optional[Email]:
        return self.email_repo.get_by_id(email_id)

    def get_email_by_source_id(self, source_id: int) -> Optional[Email]:
        return self.email_repo.get_by_source_id(source_id)

    def get_not_processed_mails(self) -> List[Email]:
        return self.email_repo.get_unprocessed()

    def update_email_status(self, email_ids: List[int]) -> None:
        self.email_repo.mark_as_processed(email_ids)

    def get_attachment_by_id(self, attachment_id: str) -> Optional[Attachment]:
        return self.attachment_repo.get_by_id(attachment_id)

    def save_attachment(self, attachment: Attachment) -> Attachment:
        return self.attachment_repo.add(attachment)

    def get_attachement_data(self, source_id: int) -> Optional[Attachment]:
        return self.attachment_repo.get_by_source_id(source_id)

    def get_attachments_by_source_id(self, source_id: int) -> List[Attachment]:
        return self.attachment_repo.get_all_by_source_id(source_id)

    def get_attachments_by_email_id(self, email_id: int) -> List[Attachment]:
        email = self.email_repo.get_by_id(email_id)
        if not email or not email.source_id:
            return []
        return self.attachment_repo.get_all_by_source_id(email.source_id)

    def check_duplicate_file_by_hash(self, file_hash: str, user_id: int = None) -> DuplicateCheckResult:
        return self.attachment_repo.check_duplicate_by_hash(file_hash, user_id)

    def get_attachment_by_hash(self, file_hash: str) -> Optional[Attachment]:
        return self.attachment_repo.get_by_file_hash(file_hash)

    def save_attachment_with_hash(self, attachment: Attachment, file_hash: str) -> Attachment:
        return self.attachment_repo.save_with_hash(attachment, file_hash)

    def update_attachment_text(self, attachment_id: int, extracted_text: str) -> Optional[Attachment]:
        return self.attachment_repo.update_extracted_text(attachment_id, extracted_text)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.user_repo.get_by_id(user_id)

    def update_user_details(self, user_id: int, updated_details: dict) -> Optional[User]:
        return self.user_repo.update_details(user_id, updated_details)

    def get_user_integrations(self, user_id: int) -> List[IntegrationStatus]:
        return self.integration_repo.get_user_integrations(user_id)

    def create_expense(self, expense: Expense) -> Expense:
        return self.expense_repo.add(expense)

    def list_expenses(self, user_id: int, limit: int, offset: int) -> Dict[str, Any]:
        return self.expense_repo.list_for_user(user_id, limit, offset)

    def get_expense(self, expense_uuid: str, user_id: int) -> Optional[Expense]:
        return self.expense_repo.get_by_uuid(expense_uuid, user_id)

    def update_expense(self, expense: Expense, data: dict) -> Expense:
        return self.expense_repo.update_expense(expense, data)

    def soft_delete_expense(self, expense: Expense) -> Expense:
        return self.expense_repo.soft_delete_expense(expense)

    def get_user_id_from_integration_status(self) -> List[Tuple[int, str]]:
        return self.integration_repo.get_connected_integrations()

    def update_sync_data(self, integration_id: str) -> None:
        self.integration_repo.update_sync_data(integration_id)

    def get_expired_token_user_ids(self) -> List[int]:
        return self.integration_repo.get_expired_token_user_ids()

    def get_integration_by_slug(self, slug: str) -> Optional[Integration]:
        return self.integration_repo.get_master_by_slug(slug)

    def get_integration_features(self, integration_id: int) -> List[Tuple[IntegrationFeature, Feature]]:
        return self.integration_repo.get_integration_features(integration_id)

    def link_user_integration_to_master(self, user_integration_id: str, integration_master_id: int) -> Optional[IntegrationStatus]:
        return self.integration_repo.link_to_master(user_integration_id, integration_master_id)

    def get_user_subscription(self, user_id: int):
        return self.subscription_repo.get_active_subscription(user_id)

    def get_all_features(self) -> List[Feature]:
        return self.subscription_repo.get_all_active_features()

    def get_feature_by_key(self, feature_key: str) -> Optional[Feature]:
        return self.subscription_repo.get_feature_by_key(feature_key)

    def get_plan_features(self, plan_id: int):
        return self.subscription_repo.get_plan_features(plan_id)

    def can_use_feature(self, user_id: int, feature_key: str) -> Tuple[bool, str]:
        return self.subscription_repo.can_use_feature(user_id, feature_key)

    def save_proccessed_email_data(self, processed_email_data: ProcessedEmailData) -> Optional[ProcessedEmailData]:
        return self.document_repo.save_processed_data(processed_email_data)

    def get_processed_data(self, user_id: int, limit: int, offset: int) -> Dict[str, Any]:
        return self.document_repo.get_paginated_for_user(user_id, limit, offset)

    def get_processed_data_by_id(self, processed_data_id: int) -> Optional[ProcessedEmailData]:
        return self.document_repo.get_by_id(processed_data_id)

    def import_processed_data(self, processed_data_id: int) -> None:
        self.document_repo.mark_as_imported(processed_data_id)

    def save_processed_items(self, processed_email_id: int, items_data: list) -> None:
        self.document_repo.save_processed_items(processed_email_id, items_data)

    def get_pending_staged_documents(self, limit: int = 10):
        return self.document_repo.get_pending_staged_documents(limit)

    def update_staging_status(
        self,
        staging_id: int,
        status: str,
        error_message: str = None,
        attempts: int = None,
        metadata: dict = None
    ):
        return self.document_repo.update_staging_status(
            staging_id, status, error_message, attempts, metadata
        )
