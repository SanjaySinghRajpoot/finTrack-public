from typing import Any
from app.services.llm.base import BaseLLMProcessor
from app.services.llm.models import DocumentProcessingRequest
from app.utils.utils import create_processed_email_data


class ManualDocumentProcessor(BaseLLMProcessor):
    """Concrete processor for manual document uploads."""
    
    def extract_metadata(self, item: Any, idx: int) -> tuple[str, int, int, str]:
        """Extract text content from DocumentProcessingRequest."""
        if not isinstance(item, DocumentProcessingRequest):
            raise ValueError(f"Invalid document data at index {idx}")

        text_chunk = item.text_content.strip() if item.text_content else ""
        source_id = item.source_id
        user_id = item.user_id
        doc_type = item.document_type
        
        return text_chunk, source_id, user_id, doc_type
    
    def format_accumulated_text(self, idx: int, text_chunk: str, source_id: int, 
                                user_id: int, additional_info: str = "") -> str:
        """Format document text with delimiters."""
        return f"\n----document{idx + 1}-start---source_id:\n{source_id}\n---user_id:\n{user_id}\n---document_type:\n{additional_info}\n---\n{text_chunk}\n----document{idx + 1}-end----\n"
    
    def save_processed_response(self, processed_data: list[dict]):
        """Save processed manual upload data to database."""
        try:
            for data in processed_data:
                source_id = data.get("source_id")
                user_id = data.get("user_id")

                # For manual uploads, we don't need to get email data
                # Extract items data before creating the processed data
                items_data = data.pop("items", [])

                data_obj = create_processed_email_data(
                    user_id=user_id,
                    source_id=source_id,
                    email_id=None,  # No email for manual uploads
                    data=data
                )
                
                # Save the processed data
                self.db.save_proccessed_email_data(data_obj)
                
                # Save items data if it exists and processed data was saved successfully
                if items_data and data_obj.id:
                    self.db.save_processed_items(data_obj.id, items_data)
                    
        except Exception as e:
            error_msg = f"Error saving manual upload response: {e}"
            print(error_msg)
            # Re-raise the exception to fail the file processing
            raise Exception(error_msg)
    
    def post_processing(self, results: list[dict]) -> list[dict]:
        """No additional post-processing needed for manual uploads."""
        return results
