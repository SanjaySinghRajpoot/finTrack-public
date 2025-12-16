from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from app.models.models import User, Plan, Subscription, SubscriptionStatus, Feature, CreditHistory
from app.services.db_service import DBService
from app.models.integration_schemas import (
    SubscriptionDetailSchema,
    CreditValidationSchema,
    CreditDeductionSchema,
    FeatureAvailabilityDetailSchema,
    AllFeaturesAvailabilitySchema,
    FeatureAccessDetailSchema,
    FeatureAccessCheckSchema,
    CreditSummarySchema,
    SubscriptionCreationSchema,
    SubscriptionUpdateSchema
)


class SubscriptionService:
    """Service class to handle subscription-related operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_service = DBService(db)
    
    def create_starter_subscription(self, user_id: int) -> SubscriptionCreationSchema:
        """
        Create a starter subscription for a new user
        
        Args:
            user_id: The ID of the user to create subscription for
            
        Returns:
            SubscriptionCreationSchema: The created subscription details
            
        Raises:
            ValueError: If user doesn't exist or already has an active subscription
        """
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Check if user already has an active subscription
        existing_subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trial])
        ).first()
        
        if existing_subscription:
            raise ValueError(f"User {user_id} already has an active subscription")
        
        # Get starter plan (must exist - created by InitialSetupService)
        starter_plan = self.db.query(Plan).filter(Plan.slug == "starter").first()
        if not starter_plan:
            raise ValueError("Starter plan not found. Please ensure initial setup has been run.")
        
        # Create subscription
        subscription = Subscription(
            user_id=user_id,
            plan_id=starter_plan.id,
            status=SubscriptionStatus.trial,
            starts_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),  # 30-day trial
            credit_balance=starter_plan.total_credits,
            total_credits_allocated=starter_plan.total_credits,
            auto_renewal=False  # Trial doesn't auto-renew
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        return SubscriptionCreationSchema(
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            plan_id=subscription.plan_id,
            plan_name=starter_plan.name,
            status=subscription.status.value,
            starts_at=subscription.starts_at,
            expires_at=subscription.expires_at,
            credit_balance=subscription.credit_balance,
            total_credits_allocated=subscription.total_credits_allocated,
            auto_renewal=subscription.auto_renewal
        )
    
    def create_starter_subscription_safe(self, user_id: int) -> Optional[SubscriptionCreationSchema]:
        """
        Create a starter subscription for a new user.
        This is a safe version that returns None instead of raising exceptions,
        useful for scenarios where subscription creation failure shouldn't block user creation.
        
        Args:
            user_id: The ID of the user to create subscription for
            
        Returns:
            SubscriptionCreationSchema or None: The created subscription details or None if failed
        """
        try:
            subscription_result = self.create_starter_subscription(user_id)
            print(f"Created subscription {subscription_result.subscription_id} for user {user_id}")
            return subscription_result
        except Exception as e:
            print(f"Warning: Could not create starter subscription for user {user_id}: {e}")
            return None

    def get_user_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """
        Get the active subscription for a user
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Subscription or None: The active subscription if found
        """
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trial])
        ).first()
    
    def update_subscription_status(self, subscription_id: int, status: SubscriptionStatus) -> SubscriptionUpdateSchema:
        """
        Update the status of a subscription
        
        Args:
            subscription_id: The ID of the subscription to update
            status: The new status
            
        Returns:
            SubscriptionUpdateSchema: The updated subscription details
            
        Raises:
            ValueError: If subscription not found
        """
        subscription = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        
        if not subscription:
            raise ValueError(f"Subscription with ID {subscription_id} not found")
        
        subscription.status = status
        subscription.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(subscription)
        
        return SubscriptionUpdateSchema(
            subscription_id=subscription.id,
            status=subscription.status.value,
            updated_at=subscription.updated_at
        )
    
    def deduct_credits(self, user_id: int, credits_to_deduct: int) -> bool:
        """
        Deduct credits from user's active subscription
        
        Args:
            user_id: The ID of the user
            credits_to_deduct: Number of credits to deduct
            
        Returns:
            bool: True if credits were successfully deducted, False if insufficient credits
            
        Raises:
            ValueError: If user has no active subscription
        """
        subscription = self.get_user_active_subscription(user_id)
        
        if not subscription:
            raise ValueError(f"User {user_id} has no active subscription")
        
        if subscription.credit_balance < credits_to_deduct:
            return False  # Insufficient credits
        
        subscription.credit_balance -= credits_to_deduct
        subscription.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return True

    def get_feature_credit_cost(self, feature_key: str) -> int:
        """
        Get the credit cost for a specific feature from the Features table
        
        Args:
            feature_key: The feature key to look up (e.g., "GMAIL_SYNC")
            
        Returns:
            int: The credit cost for the feature
            
        Raises:
            ValueError: If feature not found
        """
        feature = self.db.query(Feature).filter(Feature.feature_key == feature_key).first()
        
        if not feature:
            raise ValueError(f"Feature '{feature_key}' not found. Please ensure initial setup has been run.")
        
        return feature.credit_cost
    
    def validate_credits_for_feature(self, user_id: int, feature_key: str) -> CreditValidationSchema:
        """
        Validate if user has sufficient credits for a specific feature
        
        Args:
            user_id: The ID of the user
            feature_key: The feature key to check
            
        Returns:
            CreditValidationSchema: Validation result with status, message, and credit info
        """
        # Get user's active subscription
        active_subscription = self.get_user_active_subscription(user_id)
        
        if not active_subscription:
            return CreditValidationSchema(
                valid=False,
                error_code="NO_SUBSCRIPTION",
                message="No active subscription found. Please upgrade your plan.",
                current_credits=0,
                required_credits=0
            )
        
        # Get feature credit cost
        required_credits = self.get_feature_credit_cost(feature_key)
        
        if active_subscription.credit_balance < required_credits:
            return CreditValidationSchema(
                valid=False,
                error_code="INSUFFICIENT_CREDITS",
                message=f"Insufficient credits. Required: {required_credits}, Available: {active_subscription.credit_balance}",
                current_credits=active_subscription.credit_balance,
                required_credits=required_credits
            )
        
        return CreditValidationSchema(
            valid=True,
            message="Sufficient credits available",
            current_credits=active_subscription.credit_balance,
            required_credits=required_credits
        )
    
    def deduct_credits_for_feature(self, user_id: int, feature_key: str) -> CreditDeductionSchema:
        """
        Deduct credits for a specific feature usage
        
        Args:
            user_id: The ID of the user
            feature_key: The feature key being used
            
        Returns:
            CreditDeductionSchema: Result of credit deduction with remaining balance
        """
        # Validate credits first
        validation = self.validate_credits_for_feature(user_id, feature_key)
        if not validation.valid:
            return CreditDeductionSchema(
                success=False,
                message=validation.message,
                error=validation.message,
                error_code=validation.error_code,
                credits_deducted=0,
                remaining_credits=validation.current_credits
            )
        
        # Deduct credits
        credits_to_deduct = validation.required_credits
        credit_deducted = self.deduct_credits(user_id, credits_to_deduct)
        
        if credit_deducted:
            # Record credit history transaction
            self.record_credit_history(user_id, feature_key, credits_to_deduct)
            
            # Get updated subscription for remaining balance
            updated_subscription = self.get_user_active_subscription(user_id)
            remaining_credits = updated_subscription.credit_balance if updated_subscription else 0
            
            return CreditDeductionSchema(
                success=True,
                message=f"Credits deducted successfully for {feature_key}",
                credits_deducted=credits_to_deduct,
                remaining_credits=remaining_credits
            )
        else:
            return CreditDeductionSchema(
                success=False,
                message="Credit deduction failed",
                error="Credit deduction failed",
                error_code="DEDUCTION_FAILED",
                credits_deducted=0,
                remaining_credits=validation.current_credits
            )

    def record_credit_history(self, user_id: int, feature_key: str, credits_deducted: int) -> None:
        """
        Record a credit history transaction
        
        Args:
            user_id: The ID of the user
            feature_key: The feature key being used
            credits_deducted: Number of credits deducted
            
        Raises:
            ValueError: If subscription or feature not found
        """
        # Get active subscription
        subscription = self.get_user_active_subscription(user_id)
        if not subscription:
            raise ValueError(f"No active subscription found for user {user_id}")
        
        # Get feature
        feature = self.db.query(Feature).filter(Feature.feature_key == feature_key).first()
        if not feature:
            raise ValueError(f"Feature {feature_key} not found")
        
        # Calculate credits before and after
        credits_after = subscription.credit_balance
        credits_before = credits_after + credits_deducted
        
        # Create credit history entry
        credit_history = CreditHistory(
            subscription_id=subscription.id,
            feature_id=feature.id,
            credits_before=credits_before,
            credits_used=credits_deducted,
            credits_after=credits_after,
            action_type="deduction",
            description=f"Credits deducted for {feature.display_name}"
        )
        
        self.db.add(credit_history)
        self.db.commit()

    def get_user_subscription_details(self, user_id: int) -> SubscriptionDetailSchema:
        """
        Get comprehensive subscription details for a user including credit balance
        and plan information.
        
        Returns:
            SubscriptionDetailSchema: Subscription details
        """
        try:
            subscription = self.db_service.get_user_subscription(user_id)
            
            if not subscription:
                return SubscriptionDetailSchema(
                    has_subscription=False,
                    credit_balance=0,
                    plan_name=None,
                    subscription_status=None
                )

            return SubscriptionDetailSchema(
                has_subscription=True,
                credit_balance=subscription.credit_balance,
                plan_name=subscription.plan.name,
                plan_slug=subscription.plan.slug,
                subscription_status=subscription.status.value,
                expires_at=subscription.expires_at,
                auto_renewal=subscription.auto_renewal
            )

        except Exception as e:
            raise e

    def get_feature_availability(self, user_id: int) -> Dict[str, FeatureAvailabilityDetailSchema]:
        """
        Get availability status for all features based on user's subscription
        and credit balance.
        
        Returns:
            Dict[str, FeatureAvailabilityDetailSchema]: Dictionary of feature availability
        """
        try:
            subscription = self.db_service.get_user_subscription(user_id)
            
            if not subscription:
                return {}

            # Get all features enabled for the user's plan
            plan_features = self.db_service.get_plan_features(subscription.plan_id)
            
            feature_availability = {}
            
            for plan_feature, feature in plan_features:
                credit_cost = plan_feature.custom_credit_cost or feature.credit_cost
                can_use = subscription.credit_balance >= credit_cost
                
                feature_availability[feature.feature_key] = FeatureAvailabilityDetailSchema(
                    display_name=feature.display_name,
                    description=feature.description,
                    credit_cost=credit_cost,
                    can_use=can_use,
                    category=feature.category,
                    reason="Available" if can_use else f"Insufficient credits (Required: {credit_cost}, Available: {subscription.credit_balance})"
                )

            return feature_availability

        except Exception as e:
            raise e

    def check_specific_feature_access(self, user_id: int, feature_key: str) -> FeatureAccessCheckSchema:
        """
        Check if a user can access a specific feature and return detailed information.
        
        Returns:
            FeatureAccessCheckSchema: Feature access check result
        """
        try:
            can_use, message = self.db_service.can_use_feature(user_id, feature_key)
            
            # Get additional feature details
            subscription = self.db_service.get_user_subscription(user_id)
            feature_details = None
            
            if subscription:
                plan_features = self.db_service.get_plan_features(subscription.plan_id)
                for plan_feature, feature in plan_features:
                    if feature.feature_key == feature_key:
                        credit_cost = plan_feature.custom_credit_cost or feature.credit_cost
                        feature_details = FeatureAccessDetailSchema(
                            feature_key=feature.feature_key,
                            display_name=feature.display_name,
                            description=feature.description,
                            credit_cost=credit_cost,
                            category=feature.category,
                            current_balance=subscription.credit_balance
                        )
                        break

            return FeatureAccessCheckSchema(
                can_use=can_use,
                message=message,
                feature_details=feature_details
            )

        except Exception as e:
            raise e

    def get_credit_summary(self, user_id: int) -> CreditSummarySchema:
        """
        Get a summary of user's credit usage and balance.
        
        Returns:
            CreditSummarySchema: Credit usage summary
        """
        try:
            subscription = self.db_service.get_user_subscription(user_id)
            
            if not subscription:
                return CreditSummarySchema(
                    current_balance=0,
                    total_allocated=0,
                    credits_used=0,
                    usage_percentage=0.0
                )

            credits_used = subscription.total_credits_allocated - subscription.credit_balance
            usage_percentage = (credits_used / subscription.total_credits_allocated * 100) if subscription.total_credits_allocated > 0 else 0

            return CreditSummarySchema(
                current_balance=subscription.credit_balance,
                total_allocated=subscription.total_credits_allocated,
                credits_used=credits_used,
                usage_percentage=round(usage_percentage, 2)
            )

        except Exception as e:
            raise e