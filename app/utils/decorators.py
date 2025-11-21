from functools import wraps
from fastapi import HTTPException, status
from app.services.subscription_service import SubscriptionService


def deduct_credits(feature_key: str):
    """
    Decorator that checks if the user has enough credits for the given feature_key.
    Fetches required credits from the Feature table, verifies user's subscription balance,
    deducts them if sufficient, else raises an error.
    
    Args:
        feature_key: The feature key identifier (e.g., "manual_upload", "email_processing")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user and db session from kwargs or args
            user = kwargs.get("user")
            db = kwargs.get("db")

            if not user or not db:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing user or database session."
                )

            user_id = user.get("user_id")

            # Create SubscriptionService instance
            subscription_service = SubscriptionService(db)

            # Validate and deduct credits using SubscriptionService
            result = subscription_service.deduct_credits_for_feature(user_id, feature_key)
            
            if not result.success:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=result.error or "Failed to deduct credits"
                )

            # Continue with original function
            return await func(*args, **kwargs)

        return wrapper
    return decorator
