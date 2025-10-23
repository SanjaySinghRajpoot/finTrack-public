import asyncio
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List

import requests

from app.models.models import Email
from app.services.db_service import DBService
from app.services.email_attachment_service import EmailAttachmentProcessor
from app.services.llm_service import LLMService
from app.utils.utils import create_processed_email_data


class GmailClient:
    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, access_token: str, db: DBService, user_id: int, download_dir: str = "attachments"):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {self.access_token}"}
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.db = db
        self.user_id = user_id
        self.llm_service = LLMService()

    def _get(self, endpoint: str, params: dict = None):
        """Helper for GET requests with auth header."""
        url = f"{self.BASE_URL}/{endpoint}"
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def list_messages(self, limit: int = 100):
        """
        List up to `limit` Gmail messages that are finance-related.
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
                    data = self._get("messages", params=params)
                except Exception as e:
                    logging.error(f"Unexpected error fetching Gmail messages: {e}")
                    break

                all_messages.extend(data.get("messages", []))

                if len(all_messages) >= limit or "nextPageToken" not in data:
                    break

                page_token = data["nextPageToken"]

        except Exception as e:
            logging.exception(f"Error while listing finance emails for user {self.user_id}: {e}")
            return []

        return all_messages[:limit]

    def get_message(self, msg_id: str):
        """Fetch full message details by ID."""
        return self._get(f"messages/{msg_id}", params={"format": "full"})

    def _extract_headers(self, headers_list):
        """Extract subject and from address."""
        subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers_list if h["name"] == "From"), "")
        return subject, sender

    def _decode_body(self, payload):
        """Decode plain text body."""
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

    async def fetch_emails(self):
        """
        Fetch emails with subject, sender, body, and attachments (if any).
        - Processes emails in batches of 10.
        - Waits 2 seconds between batches to avoid hitting Gmail API limits.
        - Handles both attachment and non-attachment emails gracefully.
        """
        try:
            messages = self.list_messages()  # Max 100 messages per call
            total_messages = len(messages)

            if not total_messages:
                print("No new emails found.")
                return []

            print(f"Found {total_messages} messages. Starting batch processing...")

            BATCH_SIZE = 10
            TIMEOUT_BETWEEN_BATCHES = 2  # seconds
            total_batches = (total_messages + BATCH_SIZE - 1) // BATCH_SIZE

            processed_emails = []

            for start in range(0, total_messages, BATCH_SIZE):
                batch = messages[start:start + BATCH_SIZE]
                batch_number = (start // BATCH_SIZE) + 1
                print(f"\n➡️ Processing batch {batch_number}/{total_batches}")

                # Process each message in the batch
                for msg in batch:
                    msg_id = msg.get("id")
                    if not msg_id:
                        print("⚠️ Skipping message with no ID.")
                        continue

                    # Skip already processed emails
                    if self.db.get_email_by_id(msg_id):
                        print(f"✅ Already processed message {msg_id}")
                        continue

                    msg_data = self.get_message(msg_id)
                    payload = msg_data.get("payload", {})
                    headers_list = payload.get("headers", [])

                    subject, sender = self._extract_headers(headers_list)
                    body = self._decode_body(payload)

                    # Create base email record
                    email_obj = self._create_email_record(
                        msg_id=msg_id,
                        sender=sender,
                        subject=subject,
                        plain_text_content=body
                    )

                    # Determine if email has attachments
                    has_attachments = self._has_attachments(payload)

                    if has_attachments:
                        attachments = await self._process_email_attachments(msg_id, payload, email_obj)
                    else:
                        attachments = []
                        self._process_email_content(email_obj)

                    processed_emails.append({
                        "id": msg_id,
                        "from": sender,
                        "subject": subject,
                        "body": body.strip(),
                        "attachments": attachments,
                    })

                # Delay between batches
                if start + BATCH_SIZE < total_messages:
                    print(f"⏳ Waiting {TIMEOUT_BETWEEN_BATCHES}s before next batch...")
                    await asyncio.sleep(TIMEOUT_BETWEEN_BATCHES)

            print(f"\n✅ Completed processing {len(processed_emails)} emails.")
            return processed_emails

        except Exception as e:
            print(f"❌ Error while fetching emails: {e}")
            raise

    # ---------------------- Helper Functions ----------------------

    def _create_email_record(self, msg_id: str, sender: str, subject: str, plain_text_content: str):
        """Create and store an email record in the database."""
        email = Email(
            from_address=sender,
            subject=subject,
            type="email",
            gmail_message_id=msg_id,
            user_id=self.user_id,
            plain_text_content=plain_text_content
        )
        return self.db.add(email)

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
            )
            attachments = await email_attachments.download_attachments(
                msg_id, email_obj, payload
            )
            print(f"📎 Processed attachments for message {msg_id}")
        except Exception as e:
            print(f"⚠️ Failed to process attachments for {msg_id}: {e}")
        return attachments

    def _process_email_content(self, email_obj : Email) -> None:
        """Handle emails without attachments (plain text content)."""
        try:
            response = self.llm_service.call_gemini(text_content=email_obj.plain_text_content)
            if not response.get("is_processing_valid"):
                return
            processed_data_obj = create_processed_email_data(user_id=self.user_id, email_id=email_obj.id, data=response)
            self.db.save_proccessed_email_data(processed_email_data=processed_data_obj)
            print(f"✉️ Processed non-attachment email: id={email_obj.gmail_message_id}")
        except Exception as e:
            print(f"⚠️ Error processing plain email content for {email_obj.gmail_message_id}: {e}")