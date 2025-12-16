"""Subscription Repository Module"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload

from app.models.models import Subscription, Feature, PlanFeature
from app.repositories.base_repository import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):

    def __init__(self, db_session: Session):
        super().__init__(db_session, Subscription)

    def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        return (
            self.db.query(Subscription)
            .options(joinedload(Subscription.plan))
            .filter(
                Subscription.user_id == user_id,
                Subscription.status.in_(['active', 'trial'])
            )
            .order_by(Subscription.created_at.desc())
            .first()
        )

    def get_all_active_features(self) -> List[Feature]:
        return self.db.query(Feature).filter(Feature.is_active == True).all()

    def get_feature_by_key(self, feature_key: str) -> Optional[Feature]:
        return (
            self.db.query(Feature)
            .filter(Feature.feature_key == feature_key, Feature.is_active == True)
            .first()
        )

    def get_plan_features(self, plan_id: int) -> List[Tuple[PlanFeature, Feature]]:
        return (
            self.db.query(PlanFeature, Feature)
            .join(Feature, PlanFeature.feature_id == Feature.id)
            .filter(
                PlanFeature.plan_id == plan_id,
                PlanFeature.is_enabled == True,
                Feature.is_active == True
            )
            .all()
        )

    def can_use_feature(self, user_id: int, feature_key: str) -> Tuple[bool, str]:
        subscription = self.get_active_subscription(user_id)
        if not subscription:
            return False, "No active subscription found"

        feature = self.get_feature_by_key(feature_key)
        if not feature:
            return False, "Feature not found"

        plan_feature = (
            self.db.query(PlanFeature)
            .filter(
                PlanFeature.plan_id == subscription.plan_id,
                PlanFeature.feature_id == feature.id,
                PlanFeature.is_enabled == True
            )
            .first()
        )

        if not plan_feature:
            return False, "Feature not available in current plan"

        credit_cost = plan_feature.custom_credit_cost or feature.credit_cost

        if subscription.credit_balance >= credit_cost:
            return True, "Feature available"
        else:
            return False, f"Insufficient credits. Required: {credit_cost}, Available: {subscription.credit_balance}"
