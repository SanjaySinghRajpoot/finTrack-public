import os

from dotenv import load_dotenv
from starlette.responses import JSONResponse, RedirectResponse

from app.models.models import Expense, User
from app.services.s3_service import S3Service
from app.services.token_service import TokenService
from app.services.db_service import DBService
from app.services.user_service import UserService
from app.utils.oauth_utils import generate_auth_url, exchange_code_for_tokens
from app.services.gmail_service import GmailClient
from app.models.scheme import ExpenseCreate, ExpenseUpdate
from app.utils.exceptions import (
    AuthenticationError,
    NotFoundError,
    BusinessLogicError,
    ExternalServiceError,
    DatabaseError
)

load_dotenv()

VITE_API_BASE_URL = os.getenv("VITE_API_BASE_URL")


class AuthController:
    @staticmethod
    def login():
        url = generate_auth_url()
        return {"auth_url": url}

    @staticmethod
    def oauth2callback(request, code, db):
        try:
            tokens = exchange_code_for_tokens(code, db)

            token_service = TokenService(db)
            token_service.save_gmail_token(
                tokens.get("user").get("id"),
                tokens.get("user").get("email"),
                tokens.get("google_access_token"),
                tokens.get("google_refresh_token"),
                tokens.get("expires_in")
            )

            response = RedirectResponse(url= VITE_API_BASE_URL or "http://localhost:8080/")

            # Set cookies securely
            response.set_cookie(
                key="expense_tracker_jwt",
                value=tokens.get("jwt"),
                httponly=False,
                secure=True,
                samesite="Lax",
                max_age=tokens.get("expires_in")
            )

            return response
        except Exception as e:
            raise ExternalServiceError("OAuth", f"Authentication failed: {str(e)}")


class EmailController:
    @staticmethod
    async def get_emails(payload, user, db):
        user_id = user.get("user_id")

        access_token = payload.access_token
        if not access_token:
            raise AuthenticationError("Not authenticated. Please login first.")

        db_service = DBService(db)
        gmail_client = GmailClient(access_token, db_service, user_id)

        return await gmail_client.fetch_emails()


class PaymentController:
    @staticmethod
    def get_payment_info(user, db, limit: int, offset: int):
        user_id = user.get("user_id")
        db_service = DBService(db)
        return db_service.get_processed_data(user_id=user_id, limit=limit, offset=offset)


class ExpenseController:
    @staticmethod
    def create_expense(payload: ExpenseCreate, user, db):
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
                if processed_data:
                    expense.source_id = processed_data.source_id
                
                db_service.import_processed_data(payload.processed_data_id)

            return db_service.create_expense(expense)
        except Exception as e:
            raise DatabaseError(f"Failed to create expense: {str(e)}")

    @staticmethod
    def list_expenses(user, db, limit: int, offset: int):
        try:
            db_service = DBService(db)
            return db_service.list_expenses(user.get("user_id"), limit, offset)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve expenses: {str(e)}")

    @staticmethod
    def get_expense(expense_id: int, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_id, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_id))
            return expense
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve expense: {str(e)}")

    @staticmethod
    def update_expense(expense_id: int, payload: ExpenseUpdate, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_id, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_id))

            return db_service.update_expense(expense, payload.to_dict())
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update expense: {str(e)}")

    @staticmethod
    def delete_expense(expense_id: int, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_id, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_id))
            return db_service.soft_delete_expense(expense)
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to delete expense: {str(e)}")

class AttachmentController:

    @staticmethod
    def get_attachment(email_id: int, db):
        try:
            db_service = DBService(db)
            # Get attachments by email_id (which internally finds source_id)
            attachments = db_service.get_attachments_by_email_id(email_id)
            return attachments[0] if attachments else None
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve attachment: {str(e)}")

    @staticmethod
    def get_attachment_signed_url(email_id: int, db):
        try:
            db_service = DBService(db)
            # Get attachments by email_id (which internally finds source_id)
            attachments = db_service.get_attachments_by_email_id(email_id)
            attachment = attachments[0] if attachments else None

            if not attachment:
                raise NotFoundError("Attachment", f"for email_id {email_id}")

            s3 = S3Service()
            signed_url = s3.get_presigned_url(attachment.s3_url)

            return signed_url

        except NotFoundError:
            raise
        except Exception as e:
            raise ExternalServiceError("S3", f"Failed to generate signed URL: {str(e)}")


class UserController:

    @staticmethod
    async def get_user_info(user: dict, db):
        try:
            db_service = DBService(db)
            user1 = db_service.get_user_by_id(user.get("user_id"))
            
            if not user1:
                raise NotFoundError("User", str(user.get("user_id")))

            return user1
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user info: {str(e)}")

    @staticmethod
    async def update_user_details(user: dict, update_details: dict, db):
        try:
            db_service = DBService(db)
            db_service.update_user_details(user.get("user_id"), update_details)
        except Exception as e:
            raise DatabaseError(f"Failed to update user details: {str(e)}")

    @staticmethod
    async def get_user_settings(user: dict, db):
        try:
            user_service = UserService()
            return await user_service.get_user_settings(user, db)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user settings: {str(e)}")








