"""
Initial Setup Service

This module handles all initial data setup required for the application to work properly.
It centralizes all setup operations that should run when the application starts.
"""

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
    """
    Centralized service for handling all initial data setup.
    
    This service orchestrates the creation of:
    - Default integrations (Gmail, WhatsApp, etc.)
    - Default features (with credit costs)
    - Default subscription plans (Starter plan)
    
    Usage:
        setup_service = InitialSetupService()
        setup_service.run_initial_setup()
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the setup service.
        
        Args:
            db: Optional database session. If not provided, creates a new one.
        """
        self._db = db
        self._should_close_db = False
        
        if self._db is None:
            self._db = SessionLocal()
            self._should_close_db = True
    
    @property
    def db(self) -> Session:
        """Get the database session."""
        return self._db
    
    def run_initial_setup(self) -> None:
        """
        Run all initial setup operations.
        
        This is the main entry point that orchestrates all setup tasks.
        Call this method when the application starts.
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting Initial Setup Process")
            logger.info("=" * 60)
            
            # Step 1: Create default integrations
            self._setup_default_integrations()
            
            # Step 2: Create default features
            self._setup_default_features()
            
            # Step 3: Create default plans
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
        """
        Create default integrations (Gmail, WhatsApp, etc.) if they don't exist.
        """
        try:
            logger.info("Setting up default integrations...")
            
            integration_creation_service = IntegrationCreationService(self.db)
            integration_creation_service.create_default_integrations()
            
            # Verify integrations were created
            integration_count = self.db.query(Integration).count()
            logger.info(f"✓ Integrations setup complete. Total integrations: {integration_count}")
            
        except Exception as e:
            logger.error(f"✗ Error setting up integrations: {str(e)}")
            raise DatabaseError(
                "Failed to set up default integrations",
                details={"error": str(e), "step": "integrations"}
            )
    
    def _setup_default_features(self) -> None:
        """
        Create default features with their credit costs if they don't exist.
        
        This ensures all core features like GMAIL_SYNC, EMAIL_PROCESSING, etc.
        are available in the database.
        """
        try:
            logger.info("Setting up default features...")
            
            # Define default feature configurations
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
                # Check if feature already exists
                existing_feature = self.db.query(Feature).filter(
                    Feature.feature_key == feature_key
                ).first()
                
                if not existing_feature:
                    # Create the feature
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
            
            # Commit all features at once
            if created_count > 0:
                self.db.commit()
                logger.info(f"✓ Created {created_count} new features")
            
            # Verify features were created
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
        """
        Create default subscription plans (Starter plan) if they don't exist.
        Also links all features to the plan.
        """
        try:
            logger.info("Setting up default subscription plans...")
            
            # Check if starter plan already exists
            starter_plan = self.db.query(Plan).filter(Plan.slug == "starter").first()
            
            if not starter_plan:
                # Create starter plan
                starter_plan = Plan(
                    name="Starter Plan",
                    slug="starter",
                    price=0.0,
                    currency="INR",
                    billing_cycle="trial",
                    total_credits=100,  # Give 100 credits to start with
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
            
            # Link features to the starter plan
            self._link_features_to_plan(starter_plan)
            
            # Verify plans were created
            plan_count = self.db.query(Plan).count()
            logger.info(f"✓ Plans setup complete. Total plans: {plan_count}")
            
        except Exception as e:
            logger.error(f"✗ Error setting up plans: {str(e)}")
            raise DatabaseError(
                "Failed to set up default plans",
                details={"error": str(e), "step": "plans"}
            )
    
    def _link_features_to_plan(self, plan: Plan) -> None:
        """
        Link all available features to the given plan.
        
        Args:
            plan: The Plan object to link features to
            
        Raises:
            DatabaseError: If linking features fails
        """
        try:
            logger.info(f"Linking features to plan '{plan.name}'...")
            
            # Get all active features
            all_features = self.db.query(Feature).filter(Feature.is_active == True).all()
            
            linked_count = 0
            for feature in all_features:
                # Check if the feature is already linked to the plan
                existing_link = self.db.query(PlanFeature).filter(
                    PlanFeature.plan_id == plan.id,
                    PlanFeature.feature_id == feature.id
                ).first()
                
                if not existing_link:
                    # Create the link
                    plan_feature = PlanFeature(
                        plan_id=plan.id,
                        feature_id=feature.id,
                        is_enabled=True,
                        custom_credit_cost=None  # Use feature's default credit cost
                    )
                    self.db.add(plan_feature)
                    linked_count += 1
            
            # Commit all links at once
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
        """
        Verify that all initial setup was completed successfully.
        
        Returns:
            dict: Status of each component with counts
        """
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


# Convenience function for easy import and use
def run_initial_setup(db: Optional[Session] = None) -> None:
    setup_service = InitialSetupService(db)
    setup_service.run_initial_setup()


def verify_initial_setup(db: Optional[Session] = None) -> dict:
    setup_service = InitialSetupService(db)
    return setup_service.verify_setup()
