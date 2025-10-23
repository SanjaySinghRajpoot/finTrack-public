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
from app.services.token_service import TokenService

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
        return IntervalTrigger(hours=24)

    async def execute(self):
        """Execute the job logic"""
        try:
            logger.info(f"[{datetime.now()}] Every24HoursCronJob is running!")

            db_gen = get_db()
            db = next(db_gen)
            db_service = DBService(db)
            token_service = TokenService(db)

            # Get the integration ids as well so that we can update the data
            data = db_service.get_user_id_from_integration_status()

            # Making this more modular as we might need to fetch other integrations details as well
            for (user_id, integration_id) in data:

                # Update the integration status
                db_service.update_sync_data(integration_id=integration_id)

                access_token = token_service.get_token(user_id=user_id, provider="gmail")
                if not access_token:
                    logger.warning(f"⚠️ Skipping user {user_id}: No valid access token found.")
                    continue

                gmail_client = GmailClient(access_token, db_service, user_id)

                await gmail_client.fetch_emails()

            # Simulating some work
            logger.info("Processing task...")
            logger.info("Task completed successfully!")
        except Exception as e:
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

