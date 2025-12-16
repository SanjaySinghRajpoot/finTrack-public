"""
Repositories Package - Repository Pattern for data access.
"""

from app.repositories.base_repository import BaseRepository
from app.repositories.email_repository import EmailRepository
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.user_repository import UserRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.integration_repository import IntegrationRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.document_repository import DocumentRepository

__all__ = [
    'BaseRepository',
    'EmailRepository',
    'AttachmentRepository',
    'UserRepository',
    'ExpenseRepository',
    'IntegrationRepository',
    'SubscriptionRepository',
    'DocumentRepository',
]
