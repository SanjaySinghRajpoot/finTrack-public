import asyncio
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

import requests
from fastapi import HTTPException

from app.models.models import Email, DocumentStaging
from app.services.db_service import DBService
from app.services.email_attachment_service import EmailAttachmentProcessor
from app.utils.exceptions import (
    NotFoundError,
    ExternalServiceError,
    DatabaseError,
    BusinessLogicError,
    AuthenticationError
)

logger = logging.getLogger(__name__)


class GmailClient:
    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, access_token: str, db_service: DBService, user_id: int):
        try:
            self.access_token = access_token
            self.headers = {"Authorization": f"Bearer {self.access_token}"}
            self.db_service = db_service
            self.user_id = user_id
            self.batch_size = 10
            self.process_batch_size = None
            self._executor = ThreadPoolExecutor(max_workers=5)
        except Exception as e:
            raise BusinessLogicError("Failed to initialize Gmail client", details={"error": str(e)})

    def _get(self, endpoint: str, params: dict = None):
        """Helper for GET requests with auth header."""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            resp = requests.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError:
            if resp.status_code == 401:
                raise AuthenticationError("Gmail API authentication failed - token may be expired")
            elif resp.status_code == 403:
                raise AuthenticationError("Gmail API access forbidden - insufficient permissions")
            elif resp.status_code == 404:
                raise NotFoundError("Gmail resource", endpoint, details={"url": url})
            raise ExternalServiceError(
                "Gmail API", 
                f"HTTP {resp.status_code}: {resp.text}", 
                details={"status_code": resp.status_code, "endpoint": endpoint}
            )
        except requests.exceptions.RequestException as e:
            raise ExternalServiceError("Gmail API", f"Network error: {str(e)}", details={"endpoint": endpoint})

    async def list_messages(self, limit: int = 100):
        """List up to `limit` Gmail messages that are finance-related."""
        finance_keywords = "(subject:invoice OR subject:bill OR subject:payment OR subject:subscription OR invoice OR billing OR payment OR receipt)"
        query = f"((has:attachment AND {finance_keywords}) OR {finance_keywords}) newer_than:15d"

        all_messages = []
        page_token = None

        try:
            while len(all_messages) < limit:
                remaining = limit - len(all_messages)
                params = {
                    "maxResults": min(100, remaining),
                    "q": query,
                }
                if page_token:
                    params["pageToken"] = page_token

                try:
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(
                        self._executor,
                        lambda: self._get("messages", params=params)
                    )
                except (AuthenticationError, ExternalServiceError):
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error fetching Gmail messages: {e}")
                    raise ExternalServiceError("Gmail API", f"Failed to fetch messages: {str(e)}")

                all_messages.extend(data.get("messages", []))

                if len(all_messages) >= limit or "nextPageToken" not in data:
                    break

                page_token = data["nextPageToken"]

        except (AuthenticationError, ExternalServiceError):
            raise
        except Exception as e:
            logger.exception(f"Error while listing finance emails for user {self.user_id}: {e}")
            raise BusinessLogicError(
                f"Failed to list messages for user {self.user_id}", 
                details={"error": str(e)}
            )

        return all_messages[:limit]

    async def get_message(self, msg_id: str):
        """Fetch full message details by ID."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                lambda: self._get(f"messages/{msg_id}", params={"format": "full"})
            )
        except (AuthenticationError, ExternalServiceError, NotFoundError):
            raise
        except Exception as e:
            raise ExternalServiceError(
                "Gmail API", 
                f"Failed to fetch message {msg_id}: {str(e)}", 
                details={"message_id": msg_id}
            )

    def _extract_headers(self, headers_list):
        """Extract subject and from address."""
        subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers_list if h["name"] == "From"), "")
        return subject, sender

    def _decode_body(self, payload):
        """Decode plain text body."""
        try:
            body = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain" and "data" in part["body"]:
                        body = part["body"]["data"]
                        break
            else:
                body = payload.get("body", {}).get("data", "")

            if body:
                return base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")
            return ""
        except Exception as e:
            logger.warning(f"Failed to decode email body: {e}")
            return ""

    async def fetch_emails(self):
        """
        Fetch emails and create DocumentStaging entries for async processing.
        - Processes emails in batches of 10.
        - Waits 2 seconds between batches to avoid hitting Gmail API limits.
        - Creates DocumentStaging entries for both attachment and HTML content emails.
        """
        try:
            messages = await self.list_messages()
            total_messages = len(messages)

            if not total_messages:
                logger.info("No new emails found.")
                return []

            logger.info(f"Found {total_messages} messages. Starting batch processing...")

            BATCH_SIZE = self.batch_size
            TIMEOUT_BETWEEN_BATCHES = 2
            total_batches = (total_messages + BATCH_SIZE - 1) // BATCH_SIZE

            staged_count = 0

            for start in range(0, total_messages, BATCH_SIZE):
                batch = messages[start:start + BATCH_SIZE]
                self.process_batch_size = len(batch)
                batch_number = (start // BATCH_SIZE) + 1
                logger.info(f"Processing batch {batch_number}/{total_batches}")

                for msg in batch:
                    try:
                        msg_id = msg.get("id")
                        if not msg_id:
                            logger.warning("Skipping message with no ID.")
                            continue

                        if self.db_service.get_email_by_id(msg_id):
                            logger.debug(f"Already processed message {msg_id}")
                            continue

                        msg_data = await self.get_message(msg_id)
                        payload = msg_data.get("payload", {})
                        headers_list = payload.get("headers", [])

                        subject, sender = self._extract_headers(headers_list)
                        body = self._decode_body(payload)

                        email_obj = self._create_email_record(
                            msg_id=msg_id,
                            sender=sender,
                            subject=subject,
                            plain_text_content=body
                        )

                        has_attachments = self._has_attachments(payload)
                        
                        if has_attachments:
                            await self._create_staging_for_attachments(msg_id, payload, email_obj)
                        else:
                            await self._create_staging_for_email_content(email_obj)
                        
                        staged_count += 1

                    except (AuthenticationError, ExternalServiceError) as e:
                        logger.error(f"Critical error processing message {msg_id}: {e}")
                        raise
                    except (DatabaseError, BusinessLogicError) as e:
                        logger.warning(f"Error processing message {msg_id}: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Unexpected error processing message {msg_id}: {e}")
                        continue

                if start + BATCH_SIZE < total_messages:
                    logger.debug(f"Waiting {TIMEOUT_BETWEEN_BATCHES}s before next batch...")
                    await asyncio.sleep(TIMEOUT_BETWEEN_BATCHES)

            logger.info(f"Created {staged_count} DocumentStaging entries for async processing.")
            return {"staged_count": staged_count, "total_messages": total_messages}

        except (AuthenticationError, ExternalServiceError):
            raise
        except Exception as e:
            logger.error(f"Error while fetching emails: {e}")
            raise BusinessLogicError(
                f"Failed to fetch emails for user {self.user_id}", 
                details={"error": str(e)}
            )

    def _create_email_record(self, msg_id: str, sender: str, subject: str, plain_text_content: str):
        """Create and store an email record in the database."""
        try:
            email = Email(
                from_address=sender,
                subject=subject,
                type="email",
                gmail_message_id=msg_id,
                user_id=self.user_id,
                plain_text_content=plain_text_content
            )
            return self.db_service.add(email)
        except Exception as e:
            raise DatabaseError(
                f"Failed to create email record for message {msg_id}", 
                details={"message_id": msg_id, "error": str(e)}
            )

    def _has_attachments(self, payload: Dict[str, Any]) -> bool:
        """Check if an email payload contains any attachments."""
        parts = payload.get("parts", [])
        for part in parts:
            body = part.get("body", {})
            if "attachmentId" in body:
                return True
        return False

    async def _process_email_attachments(self, msg_id: str, payload: dict, email_obj) -> List[Dict[str, Any]]:
        """Download and process all attachments for a given email."""
        try:
            email_attachments = EmailAttachmentProcessor(
                self.access_token,
                self.db_service,
                self.user_id,
                self.process_batch_size
            )

            attachments = await email_attachments.download_attachments(
                msg_id, email_obj, payload
            )
            logger.info(f"Processed attachments for message {msg_id}")
            return attachments
        except (ExternalServiceError, DatabaseError, BusinessLogicError):
            raise
        except Exception as e:
            logger.warning(f"Failed to process attachments for {msg_id}: {e}")
            raise BusinessLogicError(
                f"Failed to process attachments for message {msg_id}", 
                details={"message_id": msg_id, "error": str(e)}
            )

    async def _create_staging_for_attachments(self, msg_id: str, payload: dict, email_obj: Email):
        """Create DocumentStaging entries for email attachments."""
        try:
            attachments = await self._process_email_attachments(msg_id, payload, email_obj)
            
            for attachment_info in attachments:
                if not attachment_info or not attachment_info.get("attachment_id"):
                    continue
                    
                attachment = self.db_service.get_attachment_by_id(attachment_info["attachment_id"])
                if not attachment:
                    logger.warning(f"Attachment not found: {attachment_info.get('attachment_id')}")
                    continue
                
                staging_entry = DocumentStaging(
                    user_id=self.user_id,
                    source_id=email_obj.source_id,
                    filename=attachment.filename,
                    file_hash=attachment.file_hash,
                    s3_key=attachment.storage_path or attachment.s3_url,
                    mime_type=attachment.mime_type,
                    file_size=attachment.size,
                    document_type="INVOICE",
                    source_type="email",
                    document_processing_status="pending",
                    meta_data={
                        "email_subject": email_obj.subject,
                        "email_from": email_obj.from_address,
                        "gmail_message_id": email_obj.gmail_message_id,
                        "has_attachment": True,
                        "attachment_id": attachment.id
                    }
                )
                self.db_service.add(staging_entry)
                logger.info(f"Created staging entry for attachment: {attachment.filename}")
                
        except (ExternalServiceError, DatabaseError, BusinessLogicError):
            raise
        except Exception as e:
            logger.warning(f"Failed to create staging entries for attachments: {e}")
            raise DatabaseError(
                f"Failed to create staging entries for email {msg_id}", 
                details={"message_id": msg_id, "error": str(e)}
            )

    async def _create_staging_for_email_content(self, email_obj: Email):
        """Create DocumentStaging entry for email HTML/text content."""
        try:
            content = email_obj.html_content or email_obj.plain_text_content
            if not content or len(content.strip()) < 50:
                logger.warning(f"Skipping email with insufficient content: {email_obj.gmail_message_id}")
                return
            
            staging_entry = DocumentStaging(
                user_id=self.user_id,
                source_id=email_obj.source_id,
                filename=f"email_{email_obj.gmail_message_id}.txt",
                file_hash=None,
                s3_key="",
                mime_type="text/plain",
                file_size=len(content),
                document_type="EMAIL_CONTENT",
                source_type="email",
                document_processing_status="pending",
                meta_data={
                    "email_subject": email_obj.subject,
                    "email_from": email_obj.from_address,
                    "gmail_message_id": email_obj.gmail_message_id,
                    "has_attachment": False,
                    "content_type": "html" if email_obj.html_content else "text"
                }
            )
            self.db_service.add(staging_entry)
            logger.info(f"Created staging entry for email content: {email_obj.subject}")
            
        except Exception as e:
            logger.warning(f"Failed to create staging entry for email content: {e}")
            raise DatabaseError(
                f"Failed to create staging entry for email {email_obj.gmail_message_id}", 
                details={"message_id": email_obj.gmail_message_id, "error": str(e)}
            )