from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.models import Integration, IntegrationFeature, Feature, IntegrationStatus
from app.services.db_service import DBService


class IntegrationService:
    """
    Service class to handle integration and integration-feature operations.
    Provides methods to manage integrations, their features, and availability checks.
    """

    def __init__(self, db: Session):
        self.db = db
        self.db_service = DBService(db)

    def get_all_integrations(self, include_inactive: bool = False) -> List[Integration]:
        """
        Get all available integrations with their features.
        
        Args:
            include_inactive: Whether to include inactive integrations
            
        Returns:
            List of Integration objects with loaded features
        """
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

    def get_integration_by_slug(self, slug: str) -> Optional[Integration]:
        """
        Get integration by its slug identifier.
        If the integration doesn't exist and it's a supported type (like gmail), create it.
        
        Args:
            slug: Integration slug (e.g., 'gmail', 'whatsapp')
            
        Returns:
            Integration object or None if not found
        """
        integration = (
            self.db.query(Integration)
            .options(
                joinedload(Integration.integration_features)
                .joinedload(IntegrationFeature.feature)
            )
            .filter(
                Integration.slug == slug,
                Integration.is_active == True
            )
            .first()
        )
        
        # If integration doesn't exist but it's a known type, create it dynamically
        if not integration and slug in ['gmail', 'whatsapp']:
            integration = self._create_integration_if_missing(slug)
            
        return integration

    def _create_integration_if_missing(self, slug: str) -> Optional[Integration]:
        """
        Create a missing integration dynamically during user signup/token save.
        
        Args:
            slug: Integration slug to create
            
        Returns:
            Created Integration object or None if creation failed
        """
        integration_definitions = {
            'gmail': {
                'name': 'Gmail',
                'description': 'Gmail email integration for processing financial documents and receipts',
                'provider': 'Google',
                'category': 'email',
                'icon_url': '/icons/gmail.svg',
                'features': ['email_processing', 'pdf_extraction', 'document_classification', 'expense_categorization']
            },
            'whatsapp': {
                'name': 'WhatsApp Business',
                'description': 'WhatsApp Business API integration for document processing',
                'provider': 'Meta',
                'category': 'messaging',
                'icon_url': '/icons/whatsapp.svg',
                'features': ['pdf_extraction', 'document_classification']
            }
        }
        
        if slug not in integration_definitions:
            return None
            
        definition = integration_definitions[slug]
        
        try:
            # Create the integration
            integration = Integration(
                name=definition['name'],
                slug=slug,
                description=definition['description'],
                provider=definition['provider'],
                category=definition['category'],
                icon_url=definition.get('icon_url'),
                is_active=True,
                display_order=99  # Put dynamically created ones at the end
            )
            
            self.db.add(integration)
            self.db.flush()  # Get the ID
            
            # Create default features if they exist
            for i, feature_key in enumerate(definition['features'], 1):
                feature = self.db.query(Feature).filter(Feature.feature_key == feature_key).first()
                if feature:
                    int_feature = IntegrationFeature(
                        integration_id=integration.id,
                        feature_id=feature.id,
                        is_enabled=True,
                        execution_order=i
                    )
                    self.db.add(int_feature)
            
            self.db.commit()
            
            # Reload with relationships
            integration = (
                self.db.query(Integration)
                .options(
                    joinedload(Integration.integration_features)
                    .joinedload(IntegrationFeature.feature)
                )
                .filter(Integration.id == integration.id)
                .first()
            )
            
            print(f"Dynamically created integration: {integration.name}")
            return integration
            
        except Exception as e:
            self.db.rollback()
            print(f"Failed to create integration {slug}: {e}")
            return None

    def get_integration_features(self, integration_id: int) -> List[Dict]:
        """
        Get all features available for a specific integration.
        
        Args:
            integration_id: ID of the integration
            
        Returns:
            List of feature dictionaries with integration-specific details
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

        features = []
        for int_feature, feature in integration_features:
            feature_data = {
                "feature_id": feature.id,
                "feature_key": feature.feature_key,
                "display_name": int_feature.custom_display_name or feature.display_name,
                "description": feature.description,
                "category": feature.category,
                "credit_cost": int_feature.custom_credit_cost or feature.credit_cost,
                "execution_order": int_feature.execution_order,
                "custom_config": int_feature.custom_config,
                "is_enabled": int_feature.is_enabled
            }
            features.append(feature_data)

        return features

    def check_integration_feature_access(self, user_id: int, integration_slug: str, feature_key: str) -> Tuple[bool, str, Dict]:
        """
        Check if a user can access a specific feature of an integration.
        
        Args:
            user_id: ID of the user
            integration_slug: Slug of the integration (e.g., 'gmail')
            feature_key: Key of the feature to check
            
        Returns:
            Tuple of (can_use: bool, message: str, details: dict)
        """
        # Get integration
        integration = self.get_integration_by_slug(integration_slug)
        if not integration:
            return False, f"Integration '{integration_slug}' not found", {}

        # Check if feature exists for this integration
        integration_feature = None
        target_feature = None
        
        for int_feat in integration.integration_features:
            if int_feat.feature.feature_key == feature_key and int_feat.is_enabled:
                integration_feature = int_feat
                target_feature = int_feat.feature
                break

        if not integration_feature:
            return False, f"Feature '{feature_key}' not available for {integration.name}", {}

        # Check user's subscription and credits using existing SubscriptionService logic
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

        return can_use, message, details

    def get_user_integration_details(self, user_id: int) -> List[Dict]:
        """
        Get detailed information about user's integrations including feature availability.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of dictionaries containing integration details with feature availability
        """
        # Get user's integration status
        user_integrations = self.db_service.get_user_integrations(user_id)
        
        integration_details = []
        
        for user_integration in user_integrations:
            # Get master integration details if linked
            master_integration = None
            if user_integration.integration_master_id:
                master_integration = (
                    self.db.query(Integration)
                    .options(
                        joinedload(Integration.integration_features)
                        .joinedload(IntegrationFeature.feature)
                    )
                    .filter(Integration.id == user_integration.integration_master_id)
                    .first()
                )

            # If no master integration linked, try to find by type
            if not master_integration:
                master_integration = self.get_integration_by_slug(user_integration.integration_type.value)

            integration_data = {
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

            # Add integration-specific config details
            if user_integration.integration_type.name.lower() == "email" and user_integration.email_config:
                integration_data.update({
                    "connected_email": user_integration.email_config.email_address,
                    "provider": user_integration.email_config.provider,
                    "verified": user_integration.email_config.verified,
                    "connected_at": user_integration.email_config.connected_at,
                    "expires_at": user_integration.email_config.expires_at,
                })
            elif user_integration.integration_type.name.lower() == "whatsapp" and user_integration.whatsapp_config:
                integration_data.update({
                    "connected_number": user_integration.whatsapp_config.phone_number,
                    "verified": user_integration.whatsapp_config.verified,
                    "connected_at": user_integration.whatsapp_config.connected_at,
                })

            # Add master integration details and features
            if master_integration:
                integration_data.update({
                    "integration_name": master_integration.name,
                    "integration_slug": master_integration.slug,
                    "provider": master_integration.provider,
                    "category": master_integration.category,
                    "description": master_integration.description,
                    "icon_url": master_integration.icon_url,
                })

                # Get feature availability for this integration
                features = []
                for int_feature in master_integration.integration_features:
                    if int_feature.is_enabled and int_feature.feature.is_active:
                        can_use, reason, details = self.check_integration_feature_access(
                            user_id, master_integration.slug, int_feature.feature.feature_key
                        )
                        
                        feature_info = {
                            "feature_key": int_feature.feature.feature_key,
                            "display_name": int_feature.custom_display_name or int_feature.feature.display_name,
                            "description": int_feature.feature.description,
                            "category": int_feature.feature.category,
                            "credit_cost": int_feature.custom_credit_cost or int_feature.feature.credit_cost,
                            "can_use": can_use,
                            "usage_reason": reason,
                            "execution_order": int_feature.execution_order
                        }
                        features.append(feature_info)

                # Sort features by execution order
                features.sort(key=lambda x: (x["execution_order"] or 999, x["display_name"]))
                integration_data["features"] = features

                # Overall integration usage check (can use if any feature is available)
                can_use_integration = any(f["can_use"] for f in features)
                primary_feature = features[0] if features else None
                
                integration_data.update({
                    "can_use_integration": can_use_integration,
                    "usage_reason": "Available" if can_use_integration else (
                        primary_feature["usage_reason"] if primary_feature else "No features available"
                    ),
                    "primary_feature": primary_feature
                })
            else:
                # Fallback for integrations without master integration
                integration_data.update({
                    "integration_name": user_integration.integration_type.value.title(),
                    "integration_slug": user_integration.integration_type.value,
                    "can_use_integration": False,
                    "usage_reason": "Integration configuration not found",
                    "features": []
                })

            integration_details.append(integration_data)

        return integration_details

    def create_default_integrations(self) -> None:
        """
        Create default integrations and their features if they don't exist.
        This method should be called during application initialization.
        """
        default_integrations = [
            {
                "name": "Gmail",
                "slug": "gmail",
                "description": "Google Gmail integration for email processing and automation",
                "provider": "Google",
                "category": "email",
                "icon_url": "/icons/gmail.svg",
                "features": [
                    {"feature_key": "GMAIL_SYNC", "execution_order": 1},
                    {"feature_key": "GMAIL_SEND", "execution_order": 2},
                    {"feature_key": "EMAIL_PROCESSING", "execution_order": 3}
                ]
            },
            {
                "name": "WhatsApp Business",
                "slug": "whatsapp",
                "description": "WhatsApp Business API integration for messaging automation",
                "provider": "Meta",
                "category": "messaging",
                "icon_url": "/icons/whatsapp.svg",
                "features": [
                    {"feature_key": "WHATSAPP_SYNC", "execution_order": 1},
                    {"feature_key": "WHATSAPP_SEND", "execution_order": 2}
                ]
            }
        ]

        for integration_data in default_integrations:
            # Check if integration already exists
            existing = self.db.query(Integration).filter(
                Integration.slug == integration_data["slug"]
            ).first()

            if not existing:
                # Create integration
                integration = Integration(
                    name=integration_data["name"],
                    slug=integration_data["slug"],
                    description=integration_data["description"],
                    provider=integration_data["provider"],
                    category=integration_data["category"],
                    icon_url=integration_data.get("icon_url"),
                    is_active=True,
                    display_order=len(default_integrations)
                )

                self.db.add(integration)
                self.db.flush()  # Get the ID

                # Create features and link them
                for feature_data in integration_data["features"]:
                    # Ensure feature exists (use existing SubscriptionService method)
                    from app.services.subscription_service import SubscriptionService
                    subscription_service = SubscriptionService(self.db)
                    
                    try:
                        feature_credit_cost = subscription_service.get_feature_credit_cost(feature_data["feature_key"])
                        feature = self.db.query(Feature).filter(
                            Feature.feature_key == feature_data["feature_key"]
                        ).first()

                        if feature:
                            # Link integration with feature
                            int_feature = IntegrationFeature(
                                integration_id=integration.id,
                                feature_id=feature.id,
                                is_enabled=True,
                                execution_order=feature_data.get("execution_order")
                            )
                            self.db.add(int_feature)
                    except Exception as e:
                        # Log error but continue with other features
                        print(f"Error creating feature {feature_data['feature_key']}: {e}")

                self.db.commit()
                print(f"Created integration: {integration.name}")