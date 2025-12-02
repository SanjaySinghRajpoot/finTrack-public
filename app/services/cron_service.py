from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from abc import ABC, abstractmethod
from datetime import datetime
from contextlib import asynccontextmanager
import logging
import os

from app.routes.routes import get_db
from app.services.db_service import DBService
from app.services.gmail_service import GmailClient
from app.services.llm_service import LLMService
from app.services.token_service import TokenService
from app.services.file_service import FileProcessor
from app.services.subscription_service import SubscriptionService
from app.models.models import Feature

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseCronJob(ABC):
    """Base class for all cron jobs"""

    def __init__(self, scheduler: AsyncIOScheduler):
        self.scheduler = scheduler
        self.job_id = self.__class__.__name__

    @abstractmethod
    async def execute(self):
        """Execute the cron job logic"""
        pass

    @abstractmethod
    def get_trigger(self):
        """Return the trigger configuration for the job"""
        pass

    def register(self):
        """Register the cron job with the scheduler"""
        trigger = self.get_trigger()
        self.scheduler.add_job(
            self.execute,
            trigger=trigger,
            id=self.job_id,
            name=self.job_id,
            replace_existing=True
        )
        logger.info(f"Registered cron job: {self.job_id}")


class Every24HoursCronJob(BaseCronJob):

    def get_trigger(self):
        return IntervalTrigger(hours=6)

    async def execute(self):
        """Execute the job logic with credit validation"""
        try:
            logger.info(f"[{datetime.now()}] Every24HoursCronJob is running!")

            db_gen = get_db()
            db = next(db_gen)
            db_service = DBService(db)
            token_service = TokenService(db)
            subscription_service = SubscriptionService(db)

            # Get the integration ids as well so that we can update the data
            data = db_service.get_user_id_from_integration_status()

            # Making this more modular as we might need to fetch other integrations details as well
            for (user_id, integration_id) in data:
                try:
                    logger.info(f"Processing Gmail sync for user {user_id}")

                    # Validate and deduct credits for Gmail sync using SubscriptionService
                    credit_result = subscription_service.deduct_credits_for_feature(user_id, "GMAIL_SYNC")
                    
                    if not credit_result.success:
                        logger.warning(f"⚠️ Skipping user {user_id}: {credit_result.error or 'Credit validation failed'}")
                        continue

                    # Update the integration status
                    db_service.update_sync_data(integration_id=integration_id)

                    # get_token is now async, so we need to await it
                    access_token = await token_service.get_token(user_id=user_id, provider="gmail")
                    if not access_token:
                        logger.warning(f"⚠️ Skipping user {user_id}: No valid access token found.")
                        continue

                    gmail_client = GmailClient(access_token, db_service, user_id)

                    # Run Gmail sync
                    sync_result = await gmail_client.fetch_emails()
                    
                    # Log results
                    if sync_result and len(sync_result) > 0:
                        logger.info(f"✅ Gmail sync completed for user {user_id}. Credits used: {credit_result.credits_deducted}, Remaining: {credit_result.remaining_credits}, Emails processed: {len(sync_result)}")
                    else:
                        logger.info(f"📭 No new emails found for user {user_id}. Credits already deducted.")

                except Exception as user_error:
                    logger.error(f"❌ Error processing user {user_id}: {str(user_error)}")
                    continue

            logger.info("Gmail sync cron job completed successfully!")
        except Exception as e:
            logger.error(f"❌ Gmail sync cron job failed: {str(e)}")
            raise e

class Every1HourTokenRefreshCronJob(BaseCronJob):

    def get_trigger(self):
        return IntervalTrigger(hours=1)

    async def execute(self):
        try:
            logger.info(f"--- Starting hourly Token Refresh CRON ---")
            db_gen = get_db()
            db = next(db_gen)
            db_service = DBService(db)
            token_service = TokenService(db)

            user_ids = db_service.get_expired_token_user_ids()

            for user_id in user_ids:
                logger.info(f"Updating token for {user_id}")
                await token_service.renew_google_token(user_id=user_id)

            logger.info("Task completed successfully!")
        except Exception as e:
            raise e

class IsEmailProcessedCheckCRON(BaseCronJob):
    def get_trigger(self):
        return IntervalTrigger(hours=6)

    async def execute(self):
        try:
            logger.info(f"--- Starting IsEmailProcessedCheckCRON ---")
            db_gen = get_db()
            db = next(db_gen)
            db_service = DBService(db)

            # Direct DB call (sync) - no executor needed
            emails = db_service.get_not_processed_mails()

            processed_emails = []
            for email in emails:

                has_attachments = False
                if email.attachments is not None:
                    has_attachments = True

                file_processor = FileProcessor(db, email.user_id)
                
                processed_emails.append({
                    "email_id": email.id,
                    "user_id": email.user_id,
                    "from": email.from_address,
                    "subject": email.subject,
                    "body": email.plain_text_content,
                    # we only process a single pdf file from the email
                    "attachments": [file_processor.convert_to_processed_attachment(email.attachments[0]).to_dict()],
                    "has_attachments": has_attachments
                })

                # Call the LLM service - wrap sync call in executor
                llm_service = LLMService(email.user_id, db_service)
                import asyncio
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: llm_service.llm_batch_processing(processed_emails)
                )

            logger.info("Task completed successfully!")
        except Exception as e:
            raise e

