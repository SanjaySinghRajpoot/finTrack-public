from pathlib import Path
from typing import Dict, List, Optional, Union
import httpx
import requests

from app.models.models import Attachment, Email
from app.services.db_service import DBService
from app.services.file_service import FileProcessor


class EmailAttachmentProcessor:
    """Example integration with email attachment processing."""
    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
    
    def __init__(self, access_token, db : DBService, user_id: int, processed_batch_size : int):
        # Use /data as default directory
        self.file_processor = FileProcessor(db, user_id)
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.db = db
        self.user_id = user_id
        self.processed_batch_size = processed_batch_size
    
    async def _get(self, endpoint: str, params: dict = None) -> Dict:
        """Placeholder for your API get method."""
        # Replace with your actual API call implementation
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self.headers, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            return {}
    
    async def download_attachments(self, msg_id: str, email_obj: Email, payload: Dict) -> List[Dict]:
        try:
            """Download and process email attachments."""
            attachments = []

            if "parts" not in payload:
                return attachments

            for part in payload["parts"]:
                body = part.get("body", {})
                if "attachmentId" in body:  # it's an attachment
                    attachment_id = body["attachmentId"]

                    attachment_data = await self._get(f"messages/{msg_id}/attachments/{attachment_id}")
                    filename = part.get("filename")

                    attachment_info = await self.file_processor.process_gmail_attachment(attachment_data, attachment_id, filename, email_id=email_obj.id)

                    attachments.append(attachment_info)
            return attachments
        except Exception as e:
            print(e)
            return [{}]
