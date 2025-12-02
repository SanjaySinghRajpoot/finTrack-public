"""Integration Creation Service"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.models import Integration, IntegrationFeature, Feature
from app.constants.integration_constants import (
    INTEGRATION_DEFINITIONS,
    DEFAULT_INTEGRATIONS,
    IntegrationMessages,
    IntegrationDefaults
)


class IntegrationCreationService:
    
    def __init__(self, db: Session):
        self._db = db
    
    @property
    def db(self) -> Session:
        return self._db
    
    def create_integration_from_definition(self, slug: str) -> Optional[Integration]:
        if slug not in INTEGRATION_DEFINITIONS:
            return None
        
        definition = INTEGRATION_DEFINITIONS[slug]
        
        try:
            integration = self._create_integration_record(slug, definition)
            self._link_features_to_integration(integration, definition['features'])
            self.db.commit()
            
            from app.services.integration.query_service import IntegrationQueryService
            query_service = IntegrationQueryService(self.db)
            integration = query_service.get_integration_with_features(integration.id)
            
            print(IntegrationMessages.INTEGRATION_CREATED.format(name=integration.name))
            return integration
            
        except Exception as e:
            self.db.rollback()
            print(IntegrationMessages.INTEGRATION_CREATION_FAILED.format(slug=slug, error=str(e)))
            return None
    
    def create_default_integrations(self) -> None:
        for integration_data in DEFAULT_INTEGRATIONS:
            existing = self.db.query(Integration).filter(
                Integration.slug == integration_data["slug"]
            ).first()

            if not existing:
                self._create_default_integration(integration_data)
    
    def _create_integration_record(self, slug: str, definition: dict) -> Integration:
        integration = Integration(
            name=definition['name'],
            slug=slug,
            description=definition['description'],
            provider=definition['provider'],
            category=definition['category'],
            icon_url=definition.get('icon_url'),
            is_active=True,
            display_order=definition.get('display_order', IntegrationDefaults.DYNAMIC_DISPLAY_ORDER)
        )
        
        self.db.add(integration)
        self.db.flush()
        return integration
    
    def _link_features_to_integration(self, integration: Integration, feature_keys: List[str]) -> None:
        for i, feature_key in enumerate(feature_keys, 1):
            feature = self.db.query(Feature).filter(Feature.feature_key == feature_key).first()
            if feature:
                int_feature = IntegrationFeature(
                    integration_id=integration.id,
                    feature_id=feature.id,
                    is_enabled=True,
                    execution_order=i
                )
                self.db.add(int_feature)
    
    def _create_default_integration(self, integration_data: dict) -> None:
        try:
            integration = Integration(
                name=integration_data["name"],
                slug=integration_data["slug"],
                description=integration_data["description"],
                provider=integration_data["provider"],
                category=integration_data["category"],
                icon_url=integration_data.get("icon_url"),
                is_active=True,
                display_order=len(DEFAULT_INTEGRATIONS)
            )

            self.db.add(integration)
            self.db.flush()

            from app.services.subscription_service import SubscriptionService
            subscription_service = SubscriptionService(self.db)
            
            for feature_data in integration_data["features"]:
                try:
                    subscription_service.get_feature_credit_cost(feature_data["feature_key"])
                    feature = self.db.query(Feature).filter(
                        Feature.feature_key == feature_data["feature_key"]
                    ).first()

                    if feature:
                        int_feature = IntegrationFeature(
                            integration_id=integration.id,
                            feature_id=feature.id,
                            is_enabled=True,
                            execution_order=feature_data.get("execution_order")
                        )
                        self.db.add(int_feature)
                except Exception as e:
                    print(f"Error creating feature {feature_data['feature_key']}: {e}")

            self.db.commit()
            print(IntegrationMessages.INTEGRATION_CREATED.format(name=integration.name))
            
        except Exception as e:
            self.db.rollback()
            print(f"Error creating default integration: {e}")
