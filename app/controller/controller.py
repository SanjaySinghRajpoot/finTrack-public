from starlette.responses import JSONResponse, RedirectResponse

from app.models.models import Expense, User
from app.services.s3_service import S3Service
from app.services.token_service import TokenService
from app.services.db_service import DBService
from app.services.user_service import UserService
from app.utils.oauth_utils import generate_auth_url, exchange_code_for_tokens
from app.services.gmail_service import GmailClient
from app.models.scheme import ExpenseCreate, ExpenseUpdate


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

            response = RedirectResponse(url="http://localhost:8080/")

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
            return {"error": str(e)}


class EmailController:
    @staticmethod
    async def get_emails(payload, user, db):
        try:
            user_id = user.get("user_id")

            access_token = payload.access_token
            if not access_token:
                return {"error": "Not authenticated. Please login first."}

            db_service = DBService(db)
            gmail_client = GmailClient(access_token, db_service, user_id)

            return await gmail_client.fetch_emails()
        except Exception as e:
            return {"error": str(e)}


class PaymentController:
    @staticmethod
    def get_payment_info(user, db, limit: int, offset: int):
        try:
            user_id = user.get("user_id")
            db_service = DBService(db)
            return db_service.get_processed_data(user_id=user_id, limit=limit, offset=offset)
        except Exception as e:
            return {"error": str(e)}


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
                expense.processed_email_id = payload.processed_data_id
                db_service.import_processed_data(payload.processed_data_id)

            return db_service.create_expense(expense)
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def list_expenses(user, db, limit: int, offset: int):
        try:
            db_service = DBService(db)
            return db_service.list_expenses(user.get("user_id"), limit, offset)
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_expense(expense_id: int, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_id, user.get("user_id"))
            if not expense:
                return {"error": "Expense not found"}
            return expense
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def update_expense(expense_id: int, payload: ExpenseUpdate, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_id, user.get("user_id"))
            if not expense:
                return {"error": "Expense not found"}
            data = {
                "amount": payload.amount,
                "currency": payload.currency,
                "category": payload.category,
                "description": payload.description
            }
            return db_service.update_expense(expense, data)
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def delete_expense(expense_id: int, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_id, user.get("user_id"))
            if not expense:
                return {"error": "Expense not found"}
            return db_service.soft_delete_expense(expense)
        except Exception as e:
            return {"error": str(e)}

class AttachmentController:

    @staticmethod
    def get_attachment(email_id: int, db):
        try:
            db_service = DBService(db)
            return db_service.get_attachement_data(email_id=email_id)
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_attachment_signed_url(email_id: int, db):
        try:
            db_service = DBService(db)
            attachment = db_service.get_attachement_data(email_id=email_id)

            s3 = S3Service()
            signed_url = s3.get_presigned_url(attachment.s3_url)

            return signed_url

        except Exception as e:
            return {"error": str(e)}


class UserController:

    @staticmethod
    async def get_user_info(user: dict, db):
        try:
            db_service = DBService(db)
            user1 =  db_service.get_user_by_id(user.get("user_id"))

            return user1
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def get_user_settings(user: dict, db):
        try:
            user_service = UserService()

            return await user_service.get_user_settings(user, db)
        except Exception as e:
            return {"error": str(e)}








