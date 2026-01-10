import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.db_config import SessionLocal
from app.models.models import Integration, Feature, Plan, PlanFeature
from app.services.integration.creation_service import IntegrationCreationService
from app.services.subscription_service import SubscriptionService
from app.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class InitialSetupService:
    
    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._should_close_db = False
        
        if self._db is None:
            self._db = SessionLocal()
            self._should_close_db = True
    
    @property
    def db(self) -> Session:
        return self._db
    
    def run_initial_setup(self) -> None:
        """Orchestrates all initial setup tasks for the application."""
        try:
            logger.info("=" * 60)
            logger.info("Starting Initial Setup Process")
            logger.info("=" * 60)
            
            self._setup_default_integrations()
            self._setup_default_features()
            self._setup_default_plans()
            
            logger.info("=" * 60)
            logger.info("Initial Setup Process Completed Successfully")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error during initial setup: {str(e)}")
            self.db.rollback()
            raise e
        finally:
            if self._should_close_db:
                self.db.close()
    
    def _setup_default_integrations(self) -> None:
        try:
            logger.info("Setting up default integrations...")
            
            integration_creation_service = IntegrationCreationService(self.db)
            integration_creation_service.create_default_integrations()
            
            integration_count = self.db.query(Integration).count()
            logger.info(f"✓ Integrations setup complete. Total integrations: {integration_count}")
            
        except Exception as e:
            logger.error(f"✗ Error setting up integrations: {str(e)}")
            raise DatabaseError(
                "Failed to set up default integrations",
                details={"error": str(e), "step": "integrations"}
            )
    
    def _setup_default_features(self) -> None:
        try:
            logger.info("Setting up default features...")
            
            feature_configs = {
                "GMAIL_SYNC": {
                    "display_name": "Gmail Sync",
                    "description": "Synchronize emails from Gmail account",
                    "credit_cost": 1,
                    "category": "integration"
                },
                "GMAIL_SEND": {
                    "display_name": "Gmail Send",
                    "description": "Send emails via Gmail",
                    "credit_cost": 1,
                    "category": "integration"
                },
                "FILE_UPLOAD": {
                    "display_name": "File Upload",
                    "description": "Upload and process PDF documents",
                    "credit_cost": 1,
                    "category": "integration"
                },
                "EMAIL_PROCESSING": {
                    "display_name": "Email Processing",
                    "description": "Process and extract data from emails",
                    "credit_cost": 1,
                    "category": "core"
                },
                "PDF_EXTRACTION": {
                    "display_name": "PDF Text Extraction",
                    "description": "Extract text and data from PDF attachments",
                    "credit_cost": 2,
                    "category": "core"
                },
                "WHATSAPP_SYNC": {
                    "display_name": "WhatsApp Sync",
                    "description": "Synchronize messages from WhatsApp",
                    "credit_cost": 1,
                    "category": "integration"
                },
                "WHATSAPP_SEND": {
                    "display_name": "WhatsApp Send",
                    "description": "Send messages via WhatsApp",
                    "credit_cost": 1,
                    "category": "integration"
                },
                "LLM_PROCESSING": {
                    "display_name": "AI Processing",
                    "description": "Process documents using AI/LLM services",
                    "credit_cost": 3,
                    "category": "ai"
                }
            }
            
            created_count = 0
            for feature_key, config in feature_configs.items():
                existing_feature = self.db.query(Feature).filter(
                    Feature.feature_key == feature_key
                ).first()
                
                if not existing_feature:
                    feature = Feature(
                        feature_key=feature_key,
                        display_name=config["display_name"],
                        description=config["description"],
                        credit_cost=config["credit_cost"],
                        category=config["category"],
                        is_active=True
                    )
                    self.db.add(feature)
                    created_count += 1
            
            if created_count > 0:
                self.db.commit()
                logger.info(f"✓ Created {created_count} new features")
            
            feature_count = self.db.query(Feature).count()
            logger.info(f"✓ Features setup complete. Total features: {feature_count}")
            
        except Exception as e:
            logger.error(f"✗ Error setting up features: {str(e)}")
            self.db.rollback()
            raise DatabaseError(
                "Failed to set up default features",
                details={"error": str(e), "step": "features"}
            )
    
    def _setup_default_plans(self) -> None:
        try:
            logger.info("Setting up default subscription plans...")
            
            starter_plan = self.db.query(Plan).filter(Plan.slug == "starter").first()
            
            if not starter_plan:
                starter_plan = Plan(
                    name="Starter Plan",
                    slug="starter",
                    price=0.0,
                    currency="INR",
                    billing_cycle="trial",
                    total_credits=100,
                    description="Free starter plan for new users",
                    is_active=True,
                    display_order=1
                )
                
                self.db.add(starter_plan)
                self.db.commit()
                self.db.refresh(starter_plan)
                logger.info(f"✓ Created starter plan: '{starter_plan.name}' (ID: {starter_plan.id}, Credits: {starter_plan.total_credits})")
            else:
                logger.info(f"✓ Starter plan already exists: '{starter_plan.name}' (ID: {starter_plan.id}, Credits: {starter_plan.total_credits})")
            
            self._link_features_to_plan(starter_plan)
            
            plan_count = self.db.query(Plan).count()
            logger.info(f"✓ Plans setup complete. Total plans: {plan_count}")
            
        except Exception as e:
            logger.error(f"✗ Error setting up plans: {str(e)}")
            raise DatabaseError(
                "Failed to set up default plans",
                details={"error": str(e), "step": "plans"}
            )
    
    def _link_features_to_plan(self, plan: Plan) -> None:
        try:
            logger.info(f"Linking features to plan '{plan.name}'...")
            
            all_features = self.db.query(Feature).filter(Feature.is_active == True).all()
            
            linked_count = 0
            for feature in all_features:
                existing_link = self.db.query(PlanFeature).filter(
                    PlanFeature.plan_id == plan.id,
                    PlanFeature.feature_id == feature.id
                ).first()
                
                if not existing_link:
                    plan_feature = PlanFeature(
                        plan_id=plan.id,
                        feature_id=feature.id,
                        is_enabled=True,
                        custom_credit_cost=None
                    )
                    self.db.add(plan_feature)
                    linked_count += 1
            
            if linked_count > 0:
                self.db.commit()
                logger.info(f"✓ Linked {linked_count} features to plan '{plan.name}'")
            else:
                logger.info(f"✓ All features already linked to plan '{plan.name}'")
            
        except Exception as e:
            logger.error(f"✗ Error linking features to plan: {str(e)}")
            self.db.rollback()
            raise DatabaseError(
                "Failed to link features to plan",
                details={
                    "error": str(e),
                    "plan_id": plan.id,
                    "plan_name": plan.name,
                    "step": "link_features"
                }
            )
    
    def verify_setup(self) -> dict:
        try:
            integration_count = self.db.query(Integration).filter(Integration.is_active == True).count()
            feature_count = self.db.query(Feature).filter(Feature.is_active == True).count()
            plan_count = self.db.query(Plan).filter(Plan.is_active == True).count()
            
            status = {
                "integrations": {
                    "count": integration_count,
                    "status": "OK" if integration_count > 0 else "MISSING"
                },
                "features": {
                    "count": feature_count,
                    "status": "OK" if feature_count > 0 else "MISSING"
                },
                "plans": {
                    "count": plan_count,
                    "status": "OK" if plan_count > 0 else "MISSING"
                },
                "overall_status": "OK" if all([integration_count > 0, feature_count > 0, plan_count > 0]) else "INCOMPLETE"
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error verifying setup: {str(e)}")
            return {"overall_status": "ERROR", "error": str(e)}


def run_initial_setup(db: Optional[Session] = None) -> None:
    setup_service = InitialSetupService(db)
    setup_service.run_initial_setup()


def verify_initial_setup(db: Optional[Session] = None) -> dict:
    setup_service = InitialSetupService(db)
    return setup_service.verify_setup()
