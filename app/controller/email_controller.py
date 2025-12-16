from app.services.db_service import DBService
from app.services.gmail_service import GmailClient
from app.utils.exceptions import AuthenticationError


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
