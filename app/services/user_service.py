from sqlalchemy.orm import Session
from app.services.db_service import DBService
from app.services.subscription_service import SubscriptionService
from app.services.integration import IntegrationService
from app.models.models import User
from app.utils.exceptions import DatabaseError


class UserService:

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user(self, user_info: dict) -> User:
        try:
            email = user_info.get("email")
            
            # Check if user exists
            user = self.db.query(User).filter(User.email == email).first()
            
            if user:
                return user
            
            # Create new user
            user = User(
                email=email,
                first_name=user_info.get("name"),
                profile_image=user_info.get("picture"),
                locale="hi",
                country="India"
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            # Create starter subscription for new user
            self._create_starter_subscription_for_user(user.id)
            
            return user
            
        except Exception as e:
            self.db.rollback()
            raise DatabaseError(
                "Failed to get or create user",
                details={"email": user_info.get("email"), "error": str(e)}
            )

    def _create_starter_subscription_for_user(self, user_id: int):
        try:
            subscription_service = SubscriptionService(self.db)
            subscription_service.create_starter_subscription_safe(user_id)
        except Exception as e:
            # Log the error but don't fail the user creation
            print(f"Warning: Could not create starter subscription for user {user_id}: {e}")

    async def get_user_settings(self, user: dict, db: Session):
        try:
            db_service = DBService(self.db)
            subscription_service = SubscriptionService(self.db)
            integration_service = IntegrationService(self.db)
            
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