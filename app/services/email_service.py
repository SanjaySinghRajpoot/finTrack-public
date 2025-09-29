from pathlib import Path
from typing import Dict, List, Optional, Union
import requests

from app.models.models import Attachment
from app.services.db_service import DBService
from app.services.file_service import FileProcessor
from app.services.llm_service import LLMService
from app.utils.utils import create_processed_email_data


class EmailAttachmentProcessor:
    """Example integration with email attachment processing."""
    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
    
    def __init__(self, access_token, db : DBService, download_dir: Optional[Union[str, Path]] = None):
        # Use /data as default directory
        self.file_processor = FileProcessor(download_dir or "/metadata")
        self.download_dir = self.file_processor.download_dir
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.llm_service = LLMService()
        self.db = db
    
    def _get(self, endpoint: str, params: dict = None) -> Dict:
        """Placeholder for your API get method."""
        # Replace with your actual API call implementation
        url = f"{self.BASE_URL}/{endpoint}"
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()
    
    def _save(self, attachment_id, attachment_info, email_fk_id, filename):
        attachment_obj = self.db.get_attachment_by_id(attachment_id)

        if not attachment_obj:
            attachment_obj = Attachment(
                email_id=email_fk_id,
                attachment_id=attachment_id,
                filename=filename,
                mime_type=attachment_info.get('mime_type'),
                size=attachment_info.get("file_size"),
                storage_path=attachment_info.get("file_path"),
                extracted_text=attachment_info.get("text_content"),
            )
            self.db.save_attachment(attachment_obj)
        else:
            print("attachment already exists, skipping ")

    def process_attachements_llm(self, attachment_info, email_fk_id, user_id=2):
        try:
            response = self.llm_service.call_gemini(text_content=attachment_info.get("text_content"))
            processed_data_obj = create_processed_email_data(user_id=user_id, email_id=email_fk_id, data=response)
            self.db.save_proccessed_email_data(processed_email_data=processed_data_obj)
        except Exception as e:
            return e
    
    def download_attachments(self, msg_id: str, email_fk_id: int, payload: Dict) -> List[Dict]:
        try:
            """Download and process email attachments."""
            attachments = []

            if "parts" not in payload:
                return attachments

            for part in payload["parts"]:
                body = part.get("body", {})
                if "attachmentId" in body:  # it's an attachment
                    attachment_id = body["attachmentId"]
                    attachment_data = self._get(f"messages/{msg_id}/attachments/{attachment_id}")
                    filename = part.get("filename")

                    # Process attachment using FileProcessor
                    attachment_info = self.file_processor.process_gmail_attachment(
                        attachment_data, attachment_id, filename
                    )

                    self.process_attachements_llm(attachment_info, email_fk_id)

                    self._save(attachment_id, attachment_info, email_fk_id, filename)

                    attachments.append(attachment_info)
            return attachments
        except Exception as e:
            print(e)
            return [{}]

