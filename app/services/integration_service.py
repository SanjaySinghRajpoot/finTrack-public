from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.models import Integration, IntegrationFeature, Feature, IntegrationStatus
from app.models.integration_schemas import (
    FeatureSchema,
    FeatureAvailabilitySchema,
    IntegrationBasicSchema,
    IntegrationWithFeaturesSchema,
    UserIntegrationDetailSchema,
    IntegrationFeatureAccessResult,
    IntegrationDefinition
)
from app.constants.integration_constants import (
    INTEGRATION_DEFINITIONS,
    DEFAULT_INTEGRATIONS,
    IntegrationMessages,
    IntegrationDefaults
)
from app.services.db_service import DBService


class IntegrationQueryService:
    """Handles database queries for integrations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_integration_with_features(self, integration_id: int) -> Optional[Integration]:
        """Load integration with all relationships"""
        return (
            self.db.query(Integration)
            .options(
                joinedload(Integration.integration_features)
                .joinedload(IntegrationFeature.feature)
            )
            .filter(Integration.id == integration_id)
            .first()
        )
    
    def get_integration_by_slug(self, slug: str, active_only: bool = True) -> Optional[Integration]:
        """Get integration by slug with features loaded"""
        query = (
            self.db.query(Integration)
            .options(
                joinedload(Integration.integration_features)
                .joinedload(IntegrationFeature.feature)
            )
            .filter(Integration.slug == slug)
        )
        
        if active_only:
            query = query.filter(Integration.is_active == True)
        
        return query.first()
    
    def get_all_integrations(self, include_inactive: bool = False) -> List[Integration]:
        """Get all integrations ordered by display_order and name"""
        query = (
            self.db.query(Integration)
            .options(
                joinedload(Integration.integration_features)
                .joinedload(IntegrationFeature.feature)
            )
            .order_by(Integration.display_order, Integration.name)
        )
        
        if not include_inactive:
            query = query.filter(Integration.is_active == True)
        
        return query.all()


class IntegrationFeatureService:
    """Handles feature-related operations for integrations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_integration_features(self, integration_id: int) -> List[FeatureSchema]:
        """Get all enabled features for an integration"""
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
            FeatureSchema(
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
            for int_feature, feature in integration_features
        ]
    
    def find_integration_feature(
        self, 
        integration: Integration, 
        feature_key: str
    ) -> Optional[Tuple[IntegrationFeature, Feature]]:
        """Find a specific feature within an integration"""
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
        """Create feature availability schema with usage check"""
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


class IntegrationCreationService:
    """Handles creation of integrations and their features"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_integration_from_definition(self, slug: str) -> Optional[Integration]:
        """Create integration from predefined definitions"""
        if slug not in INTEGRATION_DEFINITIONS:
            return None
        
        definition = INTEGRATION_DEFINITIONS[slug]
        
        try:
            integration = self._create_integration_record(slug, definition)
            self._link_features_to_integration(integration, definition['features'])
            self.db.commit()
            
            # Reload with relationships
            query_service = IntegrationQueryService(self.db)
            integration = query_service.get_integration_with_features(integration.id)
            
            print(IntegrationMessages.INTEGRATION_CREATED.format(name=integration.name))
            return integration
            
        except Exception as e:
            self.db.rollback()
            print(IntegrationMessages.INTEGRATION_CREATION_FAILED.format(slug=slug, error=str(e)))
            return None
    
    def _create_integration_record(self, slug: str, definition: dict) -> Integration:
        """Create the integration database record"""
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
        """Link features to integration with execution order"""
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
    
    def create_default_integrations(self) -> None:
        """Create default integrations if they don't exist"""
        for integration_data in DEFAULT_INTEGRATIONS:
            existing = self.db.query(Integration).filter(
                Integration.slug == integration_data["slug"]
            ).first()

            if not existing:
                self._create_default_integration(integration_data)
    
    def _create_default_integration(self, integration_data: dict) -> None:
        """Create a single default integration with features"""
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

            # Link features
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


class IntegrationService:
    """
    Main service class to handle integration and integration-feature operations.
    Provides methods to manage integrations, their features, and availability checks.
    """

    def __init__(self, db: Session):
        self.db = db
        self.db_service = DBService(db)
        self.query_service = IntegrationQueryService(db)
        self.feature_service = IntegrationFeatureService(db)
        self.creation_service = IntegrationCreationService(db)

    def get_all_integrations(self, include_inactive: bool = False) -> List[Integration]:
        """
        Get all available integrations with their features.
        
        Args:
            include_inactive: Whether to include inactive integrations
            
        Returns:
            List of Integration objects with loaded features
        """
        return self.query_service.get_all_integrations(include_inactive)

    def get_integration_by_slug(self, slug: str) -> Optional[Integration]:
        """
        Get integration by its slug identifier.
        If the integration doesn't exist and it's a supported type, create it.
        
        Args:
            slug: Integration slug (e.g., 'gmail', 'whatsapp')
            
        Returns:
            Integration object or None if not found
        """
        integration = self.query_service.get_integration_by_slug(slug)
        
        if not integration and slug in INTEGRATION_DEFINITIONS:
            integration = self.creation_service.create_integration_from_definition(slug)
            
        return integration

    def get_integration_features(self, integration_id: int) -> List[FeatureSchema]:
        """
        Get all features available for a specific integration.
        
        Args:
            integration_id: ID of the integration
            
        Returns:
            List of FeatureSchema objects
        """
        return self.feature_service.get_integration_features(integration_id)

    def check_integration_feature_access(
        self, 
        user_id: int, 
        integration_slug: str, 
        feature_key: str
    ) -> IntegrationFeatureAccessResult:
        """
        Check if a user can access a specific feature of an integration.
        
        Args:
            user_id: ID of the user
            integration_slug: Slug of the integration (e.g., 'gmail')
            feature_key: Key of the feature to check
            
        Returns:
            IntegrationFeatureAccessResult with access details
        """
        # Get integration
        integration = self.get_integration_by_slug(integration_slug)
        if not integration:
            return IntegrationFeatureAccessResult(
                can_use=False,
                message=IntegrationMessages.INTEGRATION_NOT_FOUND.format(slug=integration_slug),
                details={}
            )

        # Find feature
        result = self.feature_service.find_integration_feature(integration, feature_key)
        if not result:
            return IntegrationFeatureAccessResult(
                can_use=False,
                message=IntegrationMessages.FEATURE_NOT_AVAILABLE.format(
                    feature=feature_key, 
                    integration=integration.name
                ),
                details={}
            )
        
        integration_feature, target_feature = result

        # Check user's subscription and credits
        can_use, message = self.db_service.can_use_feature(user_id, feature_key)
        
        credit_cost = integration_feature.custom_credit_cost or target_feature.credit_cost
        
        details = {
            "integration_name": integration.name,
            "integration_slug": integration.slug,
            "feature_key": feature_key,
            "display_name": integration_feature.custom_display_name or target_feature.display_name,
            "credit_cost": credit_cost,
            "category": target_feature.category
        }

        return IntegrationFeatureAccessResult(
            can_use=can_use,
            message=message,
            details=details
        )

    def get_user_integration_details(self, user_id: int) -> List[UserIntegrationDetailSchema]:
        """
        Get detailed information about user's integrations including feature availability.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of UserIntegrationDetailSchema objects
        """
        user_integrations = self.db_service.get_user_integrations(user_id)
        
        return [
            self._build_user_integration_detail(user_id, user_integration)
            for user_integration in user_integrations
        ]
    
    def _build_user_integration_detail(
        self, 
        user_id: int, 
        user_integration: IntegrationStatus
    ) -> UserIntegrationDetailSchema:
        """Build detailed schema for a user integration"""
        # Base data
        data = {
            "integration_id": str(user_integration.id),
            "integration_type": user_integration.integration_type.value,
            "status": user_integration.status.value,
            "error_message": user_integration.error_message,
            "last_synced_at": user_integration.last_synced_at,
            "next_sync_at": user_integration.next_sync_at,
            "sync_interval_minutes": user_integration.sync_interval_minutes,
            "last_sync_duration": user_integration.last_sync_duration,
            "total_syncs": user_integration.total_syncs,
            "created_at": user_integration.created_at,
            "updated_at": user_integration.updated_at,
        }

        # Add config-specific details
        self._add_integration_config_details(data, user_integration)

        # Get master integration
        master_integration = self._get_master_integration(user_integration)

        if master_integration:
            self._add_master_integration_details(data, master_integration, user_id)
        else:
            self._add_fallback_integration_details(data, user_integration)

        return UserIntegrationDetailSchema(**data)
    
    def _add_integration_config_details(
        self, 
        data: dict, 
        user_integration: IntegrationStatus
    ) -> None:
        """Add integration-specific configuration details"""
        if user_integration.integration_type.name.lower() == "email" and user_integration.email_config:
            data.update({
                "connected_email": user_integration.email_config.email_address,
                "provider": user_integration.email_config.provider,
                "verified": user_integration.email_config.verified,
                "connected_at": user_integration.email_config.connected_at,
                "expires_at": user_integration.email_config.expires_at,
            })
        elif user_integration.integration_type.name.lower() == "whatsapp" and user_integration.whatsapp_config:
            data.update({
                "connected_number": user_integration.whatsapp_config.phone_number,
                "verified": user_integration.whatsapp_config.verified,
                "connected_at": user_integration.whatsapp_config.connected_at,
            })
    
    def _get_master_integration(self, user_integration: IntegrationStatus) -> Optional[Integration]:
        """Get master integration for a user integration"""
        if user_integration.integration_master_id:
            return self.query_service.get_integration_with_features(
                user_integration.integration_master_id
            )
        
        return self.get_integration_by_slug(user_integration.integration_type.value)
    
    def _add_master_integration_details(
        self, 
        data: dict, 
        master_integration: Integration, 
        user_id: int
    ) -> None:
        """Add master integration details and features to data"""
        data.update({
            "integration_name": master_integration.name,
            "integration_slug": master_integration.slug,
            "provider": master_integration.provider,
            "category": master_integration.category,
            "description": master_integration.description,
            "icon_url": master_integration.icon_url,
        })

        # Build feature availability list
        features = self._build_feature_availability_list(
            user_id, 
            master_integration
        )
        
        data["features"] = features
        
        # Determine overall integration usage
        can_use_integration = any(f.can_use for f in features)
        primary_feature = features[0] if features else None
        
        data.update({
            "can_use_integration": can_use_integration,
            "usage_reason": IntegrationMessages.AVAILABLE if can_use_integration else (
                primary_feature.usage_reason if primary_feature else IntegrationMessages.NO_FEATURES_AVAILABLE
            ),
            "primary_feature": primary_feature
        })
    
    def _build_feature_availability_list(
        self, 
        user_id: int, 
        master_integration: Integration
    ) -> List[FeatureAvailabilitySchema]:
        """Build list of feature availability schemas"""
        features = []
        
        for int_feature in master_integration.integration_features:
            if int_feature.is_enabled and int_feature.feature.is_active:
                feature_schema = self.feature_service.create_feature_availability(
                    user_id=user_id,
                    integration_slug=master_integration.slug,
                    feature_key=int_feature.feature.feature_key,
                    int_feature=int_feature,
                    target_feature=int_feature.feature,
                    db_service=self.db_service
                )
                features.append(feature_schema)
        
        # Sort by execution order
        features.sort(key=lambda x: (x.execution_order or 999, x.display_name))
        return features
    
    def _add_fallback_integration_details(
        self, 
        data: dict, 
        user_integration: IntegrationStatus
    ) -> None:
        """Add fallback details when master integration is not found"""
        data.update({
            "integration_name": user_integration.integration_type.value.title(),
            "integration_slug": user_integration.integration_type.value,
            "can_use_integration": False,
            "usage_reason": IntegrationMessages.INTEGRATION_CONFIG_NOT_FOUND,
            "features": []
        })

    def create_default_integrations(self) -> None:
        """
        Create default integrations and their features if they don't exist.
        This method should be called during application initialization.
        """
        self.creation_service.create_default_integrations()