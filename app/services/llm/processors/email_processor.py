from typing import Any
from app.services.llm.base import BaseLLMProcessor
from app.utils.utils import create_processed_email_data


class EmailBatchProcessor(BaseLLMProcessor):
    """Concrete processor for batch email processing."""
    
    def extract_metadata(self, item: Any, idx: int) -> tuple[str, int, int, str]:
        """Extract text content from email."""
        if not isinstance(item, dict):
            raise ValueError(f"Invalid email data at index {idx}")

        has_attachments = item.get("has_attachments", False)
        attachments = item.get("attachments", [])

        if has_attachments and isinstance(attachments, list) and attachments:
            # Pick text_content from the first attachment
            first_attachment = attachments[0]
            text_chunk = first_attachment.get("text_content", "").strip()
        else:
            # Fallback to email body
            text_chunk = (item.get("body") or "").strip()

        source_id = item.get("source_id")
        user_id = item.get("user_id")
        
        return text_chunk, source_id, user_id, ""
    
    def format_accumulated_text(self, idx: int, text_chunk: str, source_id: int, 
                                user_id: int, additional_info: str = "") -> str:
        """Format email text with delimiters."""
        return f"\n----email{idx + 1}-start---source_id:\n{source_id}\n---user_id:\n{user_id}\n---\n{text_chunk}\n----email{idx + 1}-end----\n"
    
    def save_processed_response(self, processed_data: list[dict]):
        """Save processed email data to database."""
        try:
            for data in processed_data:
                source_id = data.get("source_id")
                user_id = data.get("user_id")

                # Get the email to retrieve source_id
                email = self.db.get_email_by_source_id(source_id)
                if not email or not email.source_id:
                    print(f"Warning: Email with source_id {source_id} not found.")
                    continue

                # Extract items data before creating the processed email data
                items_data = data.pop("items", [])

                data_obj = create_processed_email_data(
                    user_id=user_id,
                    source_id=email.source_id,
                    email_id=email.id,
                    data=data
                )
                
                # Save the processed email data first
                self.db.save_proccessed_email_data(data_obj)
                
                # Save items data if it exists and processed_email_data was saved successfully
                if items_data and data_obj.id:
                    self.db.save_processed_items(data_obj.id, items_data)
                    
        except Exception as e:
            raise e
    
    def post_processing(self, results: list[dict]) -> list[dict]:
        """Update email status after processing."""
        email_ids = [r["email_id"] for r in results if "email_id" in r]
        self.db.update_email_status(email_ids)
        return results
