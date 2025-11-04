from requests import Session
from app.services.db_service import DBService
from app.services.subscription_service import SubscriptionService
from app.services.integration_service import IntegrationService


class UserService:

    async def get_user_settings(self, user: dict, db: Session):
        try:
            db_service = DBService(db)
            subscription_service = SubscriptionService(db)
            integration_service = IntegrationService(db)
            
            user_id = user.get("user_id")
            
            # Get detailed integration information with features
            integrations = integration_service.get_user_integration_details(user_id)

            # Get subscription and feature availability information
            subscription_details = subscription_service.get_user_subscription_details(user_id)
            feature_availability = subscription_service.get_feature_availability(user_id)
            credit_summary = subscription_service.get_credit_summary(user_id)

            # Combine all user settings information
            user_settings = {
                "integrations": integrations,
                "subscription": subscription_details,
                "features": feature_availability,
                "credits": credit_summary
            }

            return user_settings
        except Exception as e:
            raise e