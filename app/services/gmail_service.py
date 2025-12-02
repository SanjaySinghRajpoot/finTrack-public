import asyncio
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

import requests
from fastapi import HTTPException
from openpyxl.descriptors import String

from app.models.models import Email
from app.services.db_service import DBService
from app.services.email_attachment_service import EmailAttachmentProcessor
from app.services.llm_service import LLMService
from app.utils.utils import create_processed_email_data
from app.utils.exceptions import (
    NotFoundError,
    ExternalServiceError,
    DatabaseError,
    BusinessLogicError,
    AuthenticationError
)


class GmailClient:
    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, access_token: str, db: DBService, user_id: int):
        try:
            self.access_token = access_token
            self.headers = {"Authorization": f"Bearer {self.access_token}"}
            self.db = db
            self.user_id = user_id
            self.llm_service = LLMService(user_id=user_id, db=db)
            self.batch_size = 10
            self.process_batch_size = None
            self._executor = ThreadPoolExecutor(max_workers=5)
        except Exception as e:
            raise BusinessLogicError("Failed to initialize Gmail client", details={"error": str(e)})

    def _get(self, endpoint: str, params: dict = None):
        """Helper for GET requests with auth header - SYNC method."""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            resp = requests.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 401:
                raise AuthenticationError("Gmail API authentication failed - token may be expired")
            elif resp.status_code == 403:
                raise AuthenticationError("Gmail API access forbidden - insufficient permissions")
            elif resp.status_code == 404:
                raise NotFoundError("Gmail resource", endpoint, details={"url": url})
            else:
                raise ExternalServiceError("Gmail API", f"HTTP {resp.status_code}: {resp.text}", 
                                         details={"status_code": resp.status_code, "endpoint": endpoint})
        except requests.exceptions.RequestException as e:
            raise ExternalServiceError("Gmail API", f"Network error: {str(e)}", 
                                     details={"endpoint": endpoint})

    async def list_messages(self, limit: int = 100):
        """
        List up to `limit` Gmail messages that are finance-related (async).
        Filters for emails with:
          - keywords in subject/body (invoice, bill, payment, subscription)
          - OR attachments likely to be invoices
        Only considers emails from the last 90 days.
        """
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
                    # Run sync _get in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(
                        self._executor,
                        lambda: self._get("messages", params=params)
                    )
                except (AuthenticationError, ExternalServiceError) as e:
                    # Re-raise authentication and service errors
                    raise e
                except Exception as e:
                    logging.error(f"Unexpected error fetching Gmail messages: {e}")
                    raise ExternalServiceError("Gmail API", f"Failed to fetch messages: {str(e)}")

                all_messages.extend(data.get("messages", []))

                if len(all_messages) >= limit or "nextPageToken" not in data:
                    break

                page_token = data["nextPageToken"]

        except (AuthenticationError, ExternalServiceError) as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            logging.exception(f"Error while listing finance emails for user {self.user_id}: {e}")
            raise BusinessLogicError(f"Failed to list messages for user {self.user_id}", 
                                   details={"error": str(e)})

        return all_messages[:limit]

    async def get_message(self, msg_id: str):
        """Fetch full message details by ID (async)."""
        try:
            # Run sync _get in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                lambda: self._get(f"messages/{msg_id}", params={"format": "full"})
            )
        except (AuthenticationError, ExternalServiceError, NotFoundError) as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            raise ExternalServiceError("Gmail API", f"Failed to fetch message {msg_id}: {str(e)}", 
                                     details={"message_id": msg_id})

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
            logging.warning(f"Failed to decode email body: {e}")
            return ""

    async def fetch_emails(self):
        """
        Fetch emails with subject, sender, body, and attachments (if any) - fully async.
        - Processes emails in batches of 10.
        - Waits 2 seconds between batches to avoid hitting Gmail API limits.
        - Handles both attachment and non-attachment emails gracefully.
        """
        try:
            messages = await self.list_messages()  # Async call
            total_messages = len(messages)

            if not total_messages:
                print("No new emails found.")
                return []

            print(f"Found {total_messages} messages. Starting batch processing...")

            BATCH_SIZE = self.batch_size
            TIMEOUT_BETWEEN_BATCHES = 2  # seconds
            total_batches = (total_messages + BATCH_SIZE - 1) // BATCH_SIZE

            processed_emails = []

            for start in range(0, total_messages, BATCH_SIZE):
                batch = messages[start:start + BATCH_SIZE]
                self.process_batch_size = len(batch)
                batch_number = (start // BATCH_SIZE) + 1
                print(f"\n➡️ Processing batch {batch_number}/{total_batches}")

                # Process each message in the batch
                for msg in batch:
                    try:
                        msg_id = msg.get("id")
                        if not msg_id:
                            print("⚠️ Skipping message with no ID.")
                            continue

                        # Skip already processed emails - direct DB call (sync)
                        if self.db.get_email_by_id(msg_id):
                            print(f"✅ Already processed message {msg_id}")
                            continue

                        msg_data = await self.get_message(msg_id)  # Await async call
                        payload = msg_data.get("payload", {})
                        headers_list = payload.get("headers", [])

                        subject, sender = self._extract_headers(headers_list)
                        body = self._decode_body(payload)

                        # Create base email record - direct DB call (sync)
                        email_obj = self._create_email_record(
                            msg_id=msg_id,
                            sender=sender,
                            subject=subject,
                            plain_text_content=body
                        )

                        has_attachments = self._has_attachments(payload)
                        attachments = []
                        if has_attachments:
                            attachments = await self._process_email_attachments(msg_id, payload, email_obj)

                        processed_emails.append({
                            "email_id": email_obj.id,
                            "user_id": self.user_id,
                            "from": sender,
                            "subject": subject,
                            "body": email_obj.plain_text_content,
                            "attachments": attachments,
                            "has_attachments": has_attachments
                        })

                    except (AuthenticationError, ExternalServiceError) as e:
                        # Authentication or service errors should stop processing
                        print(f"❌ Critical error processing message {msg_id}: {e}")
                        raise e
                    except (DatabaseError, BusinessLogicError) as e:
                        # Log but continue with other messages
                        print(f"⚠️ Error processing message {msg_id}: {e}")
                        continue
                    except Exception as e:
                        print(f"⚠️ Unexpected error processing message {msg_id}: {e}")
                        continue

                # Delay between batches
                if start + BATCH_SIZE < total_messages:
                    print(f"⏳ Waiting {TIMEOUT_BETWEEN_BATCHES}s before next batch...")
                    await asyncio.sleep(TIMEOUT_BETWEEN_BATCHES)

            if len(processed_emails) != 0:
                try:
                    # Run sync LLM processing in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        self._executor,
                        lambda: self.llm_service.llm_batch_processing(processed_emails)
                    )
                except Exception as e:
                    print(f"⚠️ LLM batch processing failed: {e}")
                    # Don't fail the entire operation if LLM processing fails

            print(f"\n✅ Completed processing {len(processed_emails)} emails.")
            return processed_emails

        except (AuthenticationError, ExternalServiceError) as e:
            # Re-raise critical errors
            print(f"❌ Critical error while fetching emails: {e}")
            raise e
        except Exception as e:
            print(f"❌ Error while fetching emails: {e}")
            raise BusinessLogicError(f"Failed to fetch emails for user {self.user_id}", 
                                   details={"error": str(e)})

    # ---------------------- Helper Functions ----------------------

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
            return self.db.add(email)
        except Exception as e:
            raise DatabaseError(f"Failed to create email record for message {msg_id}", 
                              details={"message_id": msg_id, "error": str(e)})

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
        attachments = []
        try:
            email_attachments = EmailAttachmentProcessor(
                self.access_token,
                self.db,
                self.user_id,
                self.process_batch_size
            )

            # contains attachment_info
            attachments = await email_attachments.download_attachments(
                msg_id, email_obj, payload
            )
            print(f"📎 Processed attachments for message {msg_id}")
        except (ExternalServiceError, DatabaseError, BusinessLogicError) as e:
            # Re-raise our custom exceptions
            print(f"⚠️ Failed to process attachments for {msg_id}: {e}")
            raise e
        except Exception as e:
            print(f"⚠️ Failed to process attachments for {msg_id}: {e}")
            raise BusinessLogicError(f"Failed to process attachments for message {msg_id}", 
                                   details={"message_id": msg_id, "error": str(e)})
        return attachments