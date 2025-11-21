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

            # Get subscription and feature availability information (returns Pydantic models)
            subscription_details = subscription_service.get_user_subscription_details(user_id)
            feature_availability = subscription_service.get_feature_availability(user_id)
            credit_summary = subscription_service.get_credit_summary(user_id)

            # Combine all user settings information
            # Convert Pydantic models to dictionaries for JSON serialization
            user_settings = {
                "integrations": [integration.model_dump() for integration in integrations],
                "subscription": subscription_details.model_dump(),
                "features": {key: value.model_dump() for key, value in feature_availability.items()},
                "credits": credit_summary.model_dump()
            }

            return user_settings
        except Exception as e:
            raise e