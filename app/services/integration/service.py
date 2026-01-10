"""
Integration Service

Main service that orchestrates all integration-related operations.
Follows the Facade pattern for better organization.
"""

import datetime
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.models import Integration, IntegrationStatus, IntegrationState, EmailConfig
from app.models.integration_schemas import (
    FeatureSchema,
    FeatureAvailabilitySchema,
    UserIntegrationDetailSchema,
    IntegrationFeatureAccessResult,
    CreditDeductionSchema
)
from app.constants.integration_constants import (
    INTEGRATION_DEFINITIONS,
    IntegrationMessages
)
from app.services.db_service import DBService
from app.services.feature_service import FeatureService
from app.services.integration.query_service import IntegrationQueryService
from app.services.integration.creation_service import IntegrationCreationService
from app.services.integration.registry import IntegrationHandlerRegistry
from app.utils.exceptions import (
    NotFoundError,
    DatabaseError,
    SubscriptionError
)

logger = logging.getLogger(__name__)


class IntegrationService:
    
    def __init__(self, db: Session):
        self._db = db
        self._db_service = DBService(db)
        self._query_service = IntegrationQueryService(db)
        self._feature_service = FeatureService(db)
        self._creation_service = IntegrationCreationService(db)
    
    @property
    def db(self) -> Session:
        return self._db
    
    @property
    def db_service(self) -> DBService:
        return self._db_service
    
    @property
    def query_service(self) -> IntegrationQueryService:
        return self._query_service
    
    @property
    def feature_service(self) -> FeatureService:
        return self._feature_service
    
    @property
    def creation_service(self) -> IntegrationCreationService:
        return self._creation_service
    
    def _get_user_integration_by_type(self, user_id: int, integration_type: str) -> Optional[IntegrationStatus]:
        """
        Helper method to get user integration by user_id and integration type.
        Centralizes the repeated integration status query pattern.
        
        Args:
            user_id: The user's ID
            integration_type: Integration type (e.g., 'gmail', 'whatsapp')
            
        Returns:
            IntegrationStatus or None if not found
        """
        return (
            self._db.query(IntegrationStatus)
            .filter_by(user_id=user_id, integration_type=integration_type)
            .first()
        )

    def get_all_integrations(self, include_inactive: bool = False) -> List[Integration]:
        return self.query_service.get_all_integrations(include_inactive)

    def get_integration_by_slug(self, slug: str) -> Optional[Integration]:
        """
        Get integration by slug.
        
        Args:
            slug: Integration slug to look up
            
        Returns:
            Integration object or None if not found
            
        Note:
            Integrations must be created by InitialSetupService during app startup.
            This method no longer creates integrations on-demand.
        """
        return self.query_service.get_integration_by_slug(slug)

    def get_integration_features(self, integration_id: int) -> List[FeatureSchema]:
        return self.feature_service.get_integration_features(integration_id)

    def check_integration_feature_access(
        self, 
        user_id: int, 
        integration_slug: str, 
        feature_key: str
    ) -> IntegrationFeatureAccessResult:
        integration = self.get_integration_by_slug(integration_slug)
        if not integration:
            return IntegrationFeatureAccessResult(
                can_use=False,
                message=IntegrationMessages.INTEGRATION_NOT_FOUND.format(slug=integration_slug),
                details={}
            )

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

        # here there is abstraction based on the integreation type we will send the handler
        handler = IntegrationHandlerRegistry.get_handler(
            user_integration.integration_type.value,
            self.db
        )
        config_details = handler.extract_config_details(user_integration)
        data.update(config_details)

        master_integration = self._get_master_integration(user_integration)

        if master_integration:
            self._add_master_integration_details(data, master_integration, user_id)
        else:
            self._add_fallback_integration_details(data, user_integration)

        return UserIntegrationDetailSchema(**data)
    
    def _get_master_integration(self, user_integration: IntegrationStatus) -> Optional[Integration]:
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
        data.update({
            "integration_name": master_integration.name,
            "integration_slug": master_integration.slug,
            "provider": master_integration.provider,
            "category": master_integration.category,
            "description": master_integration.description,
            "icon_url": master_integration.icon_url,
        })

        features = self._build_feature_availability_list(user_id, master_integration)
        
        data["features"] = features
        
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
        
        features.sort(key=lambda x: (x.execution_order or 999, x.display_name))
        return features
    
    def _add_fallback_integration_details(
        self, 
        data: dict, 
        user_integration: IntegrationStatus
    ) -> None:
        data.update({
            "integration_name": user_integration.integration_type.value.title(),
            "integration_slug": user_integration.integration_type.value,
            "can_use_integration": False,
            "usage_reason": IntegrationMessages.INTEGRATION_CONFIG_NOT_FOUND,
            "features": []
        })

    def create_user_integration(
        self,
        user_id: int,
        email: str,
        encrypted_tokens: Dict[str, str],
        expires_at: datetime.datetime,
        provider: str = "gmail"
    ) -> EmailConfig:
        """
        Create a new user integration with email config and feature validation.
        
        Args:
            user_id: The user's ID
            email: The email address for the integration
            encrypted_tokens: Dict with encrypted_access and encrypted_refresh tokens
            expires_at: Token expiration datetime
            provider: Integration provider (default: gmail)
            
        Returns:
            EmailConfig: The created email configuration
            
        Raises:
            NotFoundError: If master integration not found
            SubscriptionError: If user lacks credits for the feature
            DatabaseError: If database operation fails
        """
        try:
            from app.services.subscription_service import SubscriptionService
            subscription_service = SubscriptionService(self._db)
            
            # Get the master integration record
            master_integration = self.get_integration_by_slug(provider)
            if not master_integration:
                raise NotFoundError("Integration", provider, details={"provider": provider})
            
            # Check if user can use this integration (validate subscription and credits)
            primary_feature_key = f"{provider.upper()}_SYNC"
            validation = subscription_service.validate_credits_for_feature(user_id, primary_feature_key)
            
            if not validation.valid:
                raise SubscriptionError(
                    f"Cannot create integration: {validation.message}",
                    details={"feature": primary_feature_key, "validation": validation.model_dump()}
                )
            
            # Create the integration status
            integration = IntegrationStatus(
                user_id=user_id,
                integration_type=provider,
                integration_master_id=master_integration.id,
                status=IntegrationState.connected,
                sync_interval_minutes=600,
            )

            self._db.add(integration)
            self._db.commit()

            # Create email config
            email_config = self._create_email_config(email, integration.id, encrypted_tokens, expires_at, provider)
            
            # Deduct credits for initial setup
            self._deduct_integration_credits(subscription_service, user_id, primary_feature_key)
            
            return email_config
            
        except (NotFoundError, SubscriptionError) as e:
            raise e
        except Exception as e:
            self._db.rollback()
            raise DatabaseError(f"Failed to create integration", details={"error": str(e)})

    def update_user_integration(
        self,
        integration: IntegrationStatus,
        email: str,
        encrypted_tokens: Dict[str, str],
        expires_at: datetime.datetime,
        provider: str = "gmail"
    ) -> EmailConfig:
        """
        Update an existing user integration with new tokens.
        
        Args:
            integration: The existing IntegrationStatus to update
            email: The email address for the integration
            encrypted_tokens: Dict with encrypted_access and encrypted_refresh tokens
            expires_at: Token expiration datetime
            provider: Integration provider (default: gmail)
            
        Returns:
            EmailConfig: The updated email configuration
            
        Raises:
            SubscriptionError: If user lacks credits for the feature
            DatabaseError: If database operation fails
        """
        try:
            from app.services.subscription_service import SubscriptionService
            subscription_service = SubscriptionService(self._db)
            
            # Ensure integration is linked to master integration
            if not integration.integration_master_id:
                master_integration = self.get_integration_by_slug(provider)
                if master_integration:
                    integration.integration_master_id = master_integration.id
            
            # Check if user can still use this integration
            primary_feature_key = f"{provider.upper()}_SYNC"
            validation = subscription_service.validate_credits_for_feature(integration.user_id, primary_feature_key)
            
            if not validation.valid:
                integration.status = IntegrationState.error
                integration.error_message = f"Integration paused: {validation.message}"
                self._db.commit()
                raise SubscriptionError(
                    f"Cannot update integration: {validation.message}",
                    details={"feature": primary_feature_key, "validation": validation.model_dump()}
                )
            
            # Update integration status to connected and clear any errors
            integration.status = IntegrationState.connected
            integration.error_message = None
            integration.updated_at = datetime.datetime.utcnow()
            
            email_config = (
                self._db.query(EmailConfig)
                .filter_by(integration_id=integration.id, provider=provider)
                .first()
            )

            if email_config:
                # Update existing email config
                email_config.credentials = encrypted_tokens
                email_config.expires_at = expires_at
                email_config.email_address = email
                email_config.updated_at = datetime.datetime.utcnow()
                self._db.commit()
                return email_config

            # If Integration exists but EmailConfig missing, create it
            email_config = self._create_email_config(email, integration.id, encrypted_tokens, expires_at, provider)
            self._db.commit()
            
            return email_config
            
        except SubscriptionError as e:
            raise e
        except Exception as e:
            self._db.rollback()
            raise DatabaseError(f"Failed to update integration", details={"error": str(e)})

    def get_user_integration(self, user_id: int, provider: str) -> Optional[IntegrationStatus]:
        """
        Get existing integration for a user and provider.
        
        Args:
            user_id: The user's ID
            provider: Integration provider (e.g., 'gmail')
            
        Returns:
            IntegrationStatus or None if not found
        """
        return (
            self._db.query(IntegrationStatus)
            .filter_by(user_id=user_id, integration_type=provider)
            .first()
        )

    def _create_email_config(
        self,
        email: str,
        integration_id: int,
        tokens: Dict[str, str],
        expires_at: datetime.datetime,
        provider: str
    ) -> EmailConfig:
        """Create new EmailConfig linked to integration."""
        try:
            email_config = EmailConfig(
                email_address=email,
                integration_id=integration_id,
                provider=provider,
                expires_at=expires_at,
                credentials=tokens,
            )

            self._db.add(email_config)
            self._db.commit()
            return email_config
        except Exception as e:
            self._db.rollback()
            raise DatabaseError(f"Failed to create email config", details={"error": str(e)})

    def _deduct_integration_credits(
        self,
        subscription_service,
        user_id: int,
        feature_key: str
    ) -> None:
        """Deduct credits for integration setup. Logs warning on failure but doesn't raise."""
        try:
            credit_result: CreditDeductionSchema = subscription_service.deduct_credits_for_feature(
                user_id, feature_key
            )
            if not credit_result.success:
                logger.warning(f"Could not deduct credits for {feature_key}: {credit_result.error}")
        except Exception as credit_error:
            logger.warning(f"Credit deduction failed: {credit_error}")
