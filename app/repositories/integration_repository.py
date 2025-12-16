"""Integration Repository Module"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload

from app.models.models import (
    IntegrationStatus, Integration, IntegrationFeature, 
    Feature, EmailConfig, IntegrationState
)
from app.repositories.base_repository import BaseRepository


class IntegrationRepository(BaseRepository[IntegrationStatus]):

    def __init__(self, db_session: Session):
        super().__init__(db_session, IntegrationStatus)

    def get_connected_integrations(self) -> List[Tuple[int, str]]:
        results = (
            self.db.query(IntegrationStatus.user_id, IntegrationStatus.id)
            .filter(IntegrationStatus.status == IntegrationState.connected.value)
            .order_by(IntegrationStatus.created_at)
            .all()
        )
        return [(row.user_id, row.id) for row in results]

    def get_user_integrations(self, user_id: int) -> List[IntegrationStatus]:
        return (
            self.db.query(IntegrationStatus)
            .options(
                joinedload(IntegrationStatus.email_config),
                joinedload(IntegrationStatus.whatsapp_config)
            )
            .filter(IntegrationStatus.user_id == user_id)
            .all()
        )

    def update_sync_data(self, integration_id: str) -> None:
        try:
            now = datetime.utcnow()

            integration_status = (
                self.db.query(IntegrationStatus)
                .filter(IntegrationStatus.id == integration_id)
                .first()
            )

            if not integration_status:
                raise ValueError(f"Integration with ID {integration_id} not found")

            integration_status.last_synced_at = now
            integration_status.next_sync_at = now + timedelta(minutes=integration_status.sync_interval_minutes)
            integration_status.last_sync_duration = (integration_status.sync_interval_minutes or 0) * 60
            integration_status.total_syncs = (integration_status.total_syncs or 0) + 1

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def get_expired_token_user_ids(self) -> List[int]:
        user_ids = (
            self.db.query(IntegrationStatus.user_id)
            .join(EmailConfig, IntegrationStatus.id == EmailConfig.integration_id)
            .all()
        )
        return [uid for (uid,) in user_ids]

    def get_master_by_slug(self, slug: str) -> Optional[Integration]:
        return (
            self.db.query(Integration)
            .filter(Integration.slug == slug, Integration.is_active == True)
            .first()
        )

    def get_integration_features(self, integration_id: int) -> List[Tuple[IntegrationFeature, Feature]]:
        return (
            self.db.query(IntegrationFeature, Feature)
            .join(Feature, IntegrationFeature.feature_id == Feature.id)
            .filter(
                IntegrationFeature.integration_id == integration_id,
                IntegrationFeature.is_enabled == True,
                Feature.is_active == True
            )
            .order_by(IntegrationFeature.execution_order.nullslast())
            .all()
        )

    def link_to_master(self, user_integration_id: str, integration_master_id: int) -> Optional[IntegrationStatus]:
        try:
            user_integration = (
                self.db.query(IntegrationStatus)
                .filter(IntegrationStatus.id == user_integration_id)
                .first()
            )
            
            if user_integration:
                user_integration.integration_master_id = integration_master_id
                self.db.commit()
                return user_integration
            
            return None
        except Exception as e:
            self.db.rollback()
            raise e
