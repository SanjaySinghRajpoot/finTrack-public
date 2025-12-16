"""
Feature Service Module

This module handles all feature-related operations for integrations.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.models import Integration, IntegrationFeature, Feature
from app.models.integration_schemas import FeatureSchema, FeatureAvailabilitySchema
from app.services.db_service import DBService


class FeatureService:
    """
    Handles feature-related operations for integrations.
    
    This service manages the features associated with integrations,
    including checking availability, validating access, and creating feature schemas.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the feature service.
        
        Args:
            db: SQLAlchemy database session
        """
        self._db = db
    
    @property
    def db(self) -> Session:
        """Get the database session."""
        return self._db
    
    def get_integration_features(self, integration_id: int) -> List[FeatureSchema]:
        """
        Get all enabled features for an integration.
        
        Args:
            integration_id: ID of the integration
            
        Returns:
            List of FeatureSchema objects
        """
        integration_features = (
            self.db.query(IntegrationFeature, Feature)
            .join(Feature, IntegrationFeature.feature_id == Feature.id)
            .filter(
                IntegrationFeature.integration_id == integration_id,
                IntegrationFeature.is_enabled == True,
                Feature.is_active == True
            )
            .order_by(IntegrationFeature.execution_order.nullslast(), Feature.display_name)
            .all()
        )

        return [
            self._create_feature_schema(int_feature, feature)
            for int_feature, feature in integration_features
        ]
    
    def find_integration_feature(
        self, 
        integration: Integration, 
        feature_key: str
    ) -> Optional[Tuple[IntegrationFeature, Feature]]:
        for int_feat in integration.integration_features:
            if int_feat.feature.feature_key == feature_key and int_feat.is_enabled:
                return int_feat, int_feat.feature
        return None
    
    def create_feature_availability(
        self,
        user_id: int,
        integration_slug: str,
        feature_key: str,
        int_feature: IntegrationFeature,
        target_feature: Feature,
        db_service: DBService
    ) -> FeatureAvailabilitySchema:
        can_use, reason = db_service.can_use_feature(user_id, feature_key)
        
        return FeatureAvailabilitySchema(
            feature_key=feature_key,
            display_name=int_feature.custom_display_name or target_feature.display_name,
            description=target_feature.description,
            category=target_feature.category,
            credit_cost=int_feature.custom_credit_cost or target_feature.credit_cost,
            can_use=can_use,
            usage_reason=reason,
            execution_order=int_feature.execution_order
        )
    
    def _create_feature_schema(
        self,
        int_feature: IntegrationFeature,
        feature: Feature
    ) -> FeatureSchema:
        return FeatureSchema(
            feature_id=feature.id,
            feature_key=feature.feature_key,
            display_name=int_feature.custom_display_name or feature.display_name,
            description=feature.description,
            category=feature.category,
            credit_cost=int_feature.custom_credit_cost or feature.credit_cost,
            execution_order=int_feature.execution_order,
            custom_config=int_feature.custom_config,
            is_enabled=int_feature.is_enabled
        )
