from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from abc import ABC, abstractmethod
from datetime import datetime
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional, Any
import logging
import os
import asyncio

from app.routes.routes import get_db
from app.services.db_service import DBService
from app.services.gmail_service import GmailClient
from app.services.llm_service import LLMService
from app.services.token_service import TokenService
from app.services.file_processor_service import FileProcessor
from app.services.subscription_service import SubscriptionService
from app.models.models import Feature

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CronJobContext:
    """Context object holding common dependencies for cron jobs"""
    db: Any
    db_service: DBService
    start_time: datetime
    job_name: str


class BaseCronJob(ABC):
    """
    Base class for all cron jobs implementing Template Method Pattern.
    
    Handles common boilerplate:
    - Database session management
    - Logging (start, completion, errors)
    - Error handling with consistent formatting
    - Execution time tracking
    
    Subclasses only need to implement:
    - get_trigger(): Define the schedule
    - run(context): The actual job logic
    """

    def __init__(self, scheduler: AsyncIOScheduler):
        self.scheduler = scheduler
        self.job_id = self.__class__.__name__

    @abstractmethod
    async def run(self, context: CronJobContext):
        """
        Execute the core cron job logic.
        Override this method in subclasses.
        
        Args:
            context: CronJobContext with db, db_service, and metadata
        """
        pass

    @abstractmethod
    def get_trigger(self):
        """Return the trigger configuration for the job"""
        pass

    def get_job_description(self) -> str:
        """Optional: Override to provide a custom job description for logging"""
        return self.job_id

    async def execute(self):
        """
        Template method that handles the execution lifecycle.
        Do not override this method - override run() instead.
        """
        start_time = datetime.now()
        job_description = self.get_job_description()
        
        logger.info(f"[{start_time}] --- Starting {job_description} ---")
        
        db = None
        db_gen = None
        
        try:
            # Setup database session
            db_gen = get_db()
            db = next(db_gen)
            db_service = DBService(db)
            
            # Create context object
            context = CronJobContext(
                db=db,
                db_service=db_service,
                start_time=start_time,
                job_name=self.job_id
            )
            
            # Execute the actual job logic
            await self.run(context)
            
            # Calculate execution time
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ {job_description} completed successfully! (Duration: {duration:.2f}s)")
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"❌ {job_description} failed after {duration:.2f}s: {str(e)}")
            raise e
            
        finally:
            # Cleanup database session
            if db_gen is not None:
                try:
                    next(db_gen, None)  # Trigger finally block in get_db()
                except StopIteration:
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

    def get_job_description(self) -> str:
        return "Gmail Sync Cron Job"

    async def run(self, context: CronJobContext):
        """Execute the job logic with credit validation"""
        token_service = TokenService(context.db)
        subscription_service = SubscriptionService(context.db)

        # Get the integration ids as well so that we can update the data
        data = context.db_service.get_user_id_from_integration_status()

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
                context.db_service.update_sync_data(integration_id=integration_id)

                # get_token is now async, so we need to await it
                access_token = await token_service.get_token(user_id=user_id, provider="gmail")
                if not access_token:
                    logger.warning(f"⚠️ Skipping user {user_id}: No valid access token found.")
                    continue

                # Use context manager to ensure proper cleanup
                async with GmailClient(access_token, context.db_service, user_id) as gmail_client:
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


class Every1HourTokenRefreshCronJob(BaseCronJob):

    def get_trigger(self):
        return IntervalTrigger(hours=1)

    def get_job_description(self) -> str:
        return "Hourly Token Refresh CRON"

    async def run(self, context: CronJobContext):
        token_service = TokenService(context.db)

        user_ids = context.db_service.get_expired_token_user_ids()

        for user_id in user_ids:
            logger.info(f"Updating token for {user_id}")
            await token_service.renew_google_token(user_id=user_id)


class IsEmailProcessedCheckCRON(BaseCronJob):
    
    def get_trigger(self):
        return IntervalTrigger(hours=6)

    def get_job_description(self) -> str:
        return "Email Processing Check CRON"

    async def run(self, context: CronJobContext):
        # Direct DB call (sync) - no executor needed
        emails = context.db_service.get_not_processed_mails()

        processed_emails = []
        for email in emails:

            has_attachments = False
            if email.attachments is not None:
                has_attachments = True

            file_processor = FileProcessor(context.db, email.user_id)
            
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

            # Call the LLM service - Pass DBService instance, not database session
            llm_service = LLMService(email.user_id, context.db_service)
            await llm_service.llm_batch_processing(processed_emails)


class DocumentStagingProcessorCron(BaseCronJob):
    """
    Processes pending documents from DocumentStaging table every 5 minutes.
    Handles both email-based documents and manual uploads.
    - Email content (HTML/text): Direct LLM processing
    - Email attachments: OCR + LLM processing
    - Manual uploads: Standard document processing
    """

    def get_trigger(self):
        """Run every 5 minutes"""
        return IntervalTrigger(seconds=6)

    def get_job_description(self) -> str:
        return "Document Staging Processor CRON"

    async def run(self, context: CronJobContext):
        """Process pending documents from staging table"""
        # Fetch pending documents (up to 10 at a time)
        pending_documents = context.db_service.get_pending_staged_documents(limit=10)

        if not pending_documents:
            logger.info("No pending documents to process")
            return

        logger.info(f"Processing {len(pending_documents)} pending documents")

        # Group documents by source type for batch processing
        email_documents = []
        manual_documents = []
        
        for doc in pending_documents:
            if doc.source_type == "email":
                email_documents.append(doc)
            else:
                manual_documents.append(doc)

        # Process email documents in batch
        if email_documents:
            await self._process_email_documents_batch(context.db_service, email_documents)
        
        # Process manual uploads individually
        if manual_documents:
            await self._process_manual_documents(context.db_service, manual_documents)

    async def _process_email_documents_batch(self, db_service: DBService, email_documents: list):
        """
        Simplified batch processing for email documents.
        Delegates all processing logic to DocumentProcessor.
        """
        try:
            for doc in email_documents:
                try:
                    # Fetch email using source_id
                    email = db_service.get_email_by_source_id(doc.source_id)
                    if not email:
                        raise Exception(f"Email not found for source_id {doc.source_id}")
                    
                    has_attachments = doc.meta_data.get("has_attachment", False)
                    
                    if has_attachments:
                        # Process email attachment
                        await self._process_email_attachment(db_service, doc, email)
                    else:
                        # Process email HTML/text content
                        await self._process_email_content(db_service, doc, email)
                    
                except Exception as doc_error:
                    # Use status manager for error handling
                    from app.services.document_staging_service import DocumentStagingStatusManager
                    status_manager = DocumentStagingStatusManager(db_service, logger)
                    status_manager.update_status_failed(
                        source_id=doc.source_id,
                        error=doc_error,
                        filename=doc.filename
                    )
                    continue
                
        except Exception as e:
            logger.error(f"❌ Error in batch email processing: {str(e)}")
            raise e

    async def _process_email_attachment(self, db_service: DBService, doc, email):
        """Process email with attachment."""
        from app.services.s3_service import S3Service
        from app.services.file_processor_service import FileProcessor
        from app.services.document_processor_service import DocumentProcessor
        
        # Get attachment
        attachment_id = doc.meta_data.get("attachment_id")
        if attachment_id:
            attachment = db_service.get_attachment_by_id(attachment_id)
        else:
            attachments = db_service.get_attachments_by_source_id(doc.source_id)
            attachment = attachments[0] if attachments else None
        
        if not attachment:
            raise Exception(f"Attachment not found for source_id {doc.source_id}")
        
        logger.info(f"Processing email attachment: {attachment.filename}")
        
        # Download file from S3
        s3_service = S3Service()
        file_data = await s3_service.download_file_from_s3(
            attachment.storage_path or attachment.s3_url
        )
        
        # Extract text if PDF and not already extracted
        text_content = attachment.extracted_text
        if not text_content and attachment.filename.lower().endswith('.pdf'):
            file_processor = FileProcessor(db_service, doc.user_id)
            text_content = file_processor.extract_text(file_data)
            
            if text_content:
                db_service.update_attachment_text(attachment.id, text_content)
        
        # Process document using DocumentProcessor
        document_processor = DocumentProcessor(db_service, doc.user_id)
        await document_processor.process_document(
            source_id=doc.source_id,
            document_type=doc.document_type or "INVOICE",
            filename=attachment.filename,
            file_data=file_data,
            text_content=text_content,
            s3_key=attachment.s3_url or attachment.storage_path,
            upload_notes=f"Email from {email.from_address}: {email.subject}",
            file_hash=attachment.file_hash
        )

    async def _process_email_content(self, db_service: DBService, doc, email):
        """Process email HTML/text content without attachment."""
        from app.services.document_processor_service import DocumentProcessor
        
        logger.info(f"Processing email content from {email.from_address}")
        
        # Get HTML or plain text content
        content = email.html_content or email.plain_text_content
        
        # Process using DocumentProcessor with HTML content handler
        document_processor = DocumentProcessor(db_service, doc.user_id)
        await document_processor.process_document(
            source_id=doc.source_id,
            document_type=doc.document_type or "INVOICE",
            html_content=content,
            email_subject=email.subject,
            email_from=email.from_address,
            upload_notes=f"Email content from {email.from_address}"
        )

    async def _process_manual_documents(self, db_service: DBService, manual_documents: list):
        """
        Process manual upload documents individually.
        All status updates are handled by DocumentProcessor.
        """
        from app.services.document_processor_service import DocumentProcessor
        from app.services.s3_service import S3Service
        
        for doc in manual_documents:
            try:
                logger.info(f"Processing manual document: {doc.filename} (source_id: {doc.source_id})")

                # Download file from S3
                s3_service = S3Service()
                file_data = await s3_service.download_file_from_s3(doc.s3_key)

                # Initialize document processor
                document_processor = DocumentProcessor(db_service, doc.user_id)

                # Extract text if PDF
                text_content = None
                if doc.filename.lower().endswith('.pdf'):
                    from app.services.file_processor_service import FileProcessor
                    file_processor = FileProcessor(db_service, doc.user_id)
                    text_content = file_processor.extract_text(file_data)

                    if text_content:
                        attachments = db_service.get_attachments_by_source_id(doc.source_id)
                        if attachments:
                            db_service.update_attachment_text(attachments[0].id, text_content)

                # Process document - all status updates handled internally
                await document_processor.process_document(
                    file_data=file_data,
                    filename=doc.filename,
                    source_id=doc.source_id,
                    document_type=doc.document_type or "INVOICE",
                    text_content=text_content,
                    s3_key=doc.s3_key,
                    upload_notes=doc.upload_notes,
                    file_hash=doc.file_hash
                )

            except Exception as doc_error:
                # Errors are handled by DocumentProcessor's status manager
                logger.error(f"❌ Failed to process manual document {doc.filename}: {str(doc_error)}")

