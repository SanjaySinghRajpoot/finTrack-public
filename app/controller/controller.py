import base64
from pathlib import Path
import requests

from app.models.models import Email

# def fetch_gmail_messages(access_token: str):
#     headers = {"Authorization": f"Bearer {access_token}"}
    
#     # Step 1: Get list of messages
#     list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
#     list_resp = requests.get(list_url, headers=headers)
#     list_resp.raise_for_status()
#     messages = list_resp.json().get("messages", [])
    
#     emails = []
    
#     # Step 2: For each message, fetch full data
#     for msg in messages[:5]:  # limit to first 5 for testing
#         msg_id = msg["id"]
#         detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
#         detail_resp = requests.get(detail_url, headers=headers, params={"format": "full"})
#         detail_resp.raise_for_status()
#         msg_data = detail_resp.json()
        
#         # Extract subject, from, body
#         headers_list = msg_data["payload"].get("headers", [])
#         subject = next((h["value"] for h in headers_list if h["name"] == "Subject"), "")
#         sender = next((h["value"] for h in headers_list if h["name"] == "From"), "")
        
#         # Body may be base64 encoded
#         body = ""
#         if "parts" in msg_data["payload"]:
#             for part in msg_data["payload"]["parts"]:
#                 if part["mimeType"] == "text/plain":
#                     body = part["body"].get("data", "")
#                     break
#         else:
#             body = msg_data["payload"]["body"].get("data", "")
        
#         if body:
#             import base64
#             body = base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")
        
#         emails.append({
#             "id": msg_id,
#             "from": sender,
#             "subject": subject,
#             "body": body.strip()
#         })
    
#     return emails

class GmailClient:
    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, access_token: str, db: requests.Session, download_dir: str = "attachments"):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {self.access_token}"}
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.db = db

    def _get(self, endpoint: str, params: dict = None):
        """Helper for GET requests with auth header."""
        url = f"{self.BASE_URL}/{endpoint}"
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def list_messages(self, max_results: int = 10):
        """List message IDs."""
        data = self._get("messages", params={"maxResults": max_results})
        return data.get("messages", [])

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

    def _download_attachments(self, msg_id, payload):
        """Download attachments if present."""
        attachments = []
        if "parts" not in payload:
            return attachments

        for part in payload["parts"]:
            body = part.get("body", {})
            if "attachmentId" in body:  # it's an attachment
                attachment_id = body["attachmentId"]
                attachment_data = self._get(f"messages/{msg_id}/attachments/{attachment_id}")
                file_data = base64.urlsafe_b64decode(attachment_data["data"])

                filename = part.get("filename") or f"attachment_{attachment_id}"
                file_path = self.download_dir / filename
                with open(file_path, "wb") as f:
                    f.write(file_data)

                attachments.append(str(file_path))
        return attachments

    def fetch_emails(self, limit: int = 5):
        """Fetch emails with subject, from, body, and attachments."""
        emails = []
        messages = self.list_messages(max_results=limit)

        for msg in messages:
            msg_id = msg["id"]
            msg_data = self.get_message(msg_id)

            headers_list = msg_data["payload"].get("headers", [])
            subject, sender = self._extract_headers(headers_list)
            body = self._decode_body(msg_data["payload"])
            attachments = self._download_attachments(msg_id, msg_data["payload"])

            email_obj = Email(
                from_address=sender,
                subject=subject,
                type="email",
                gmail_message_id=msg_id,
                user_id=2
            )

            self.db.add(email_obj)
            self.db.commit()

            emails.append({
                "id": msg_id,
                "from": sender,
                "subject": subject,
                "body": body.strip(),
                "attachments": attachments,
            })

        return emails