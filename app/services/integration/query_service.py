"""Integration Query Service"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload

from app.models.models import Integration, IntegrationFeature


class IntegrationQueryService:
    
    def __init__(self, db: Session):
        self._db = db
    
    @property
    def db(self) -> Session:
        return self._db
    
    def get_integration_with_features(self, integration_id: int) -> Optional[Integration]:
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
