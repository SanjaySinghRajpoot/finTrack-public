from typing import Any, Dict, List
from fastapi import HTTPException
from app.services.llm.base import BaseLLMProcessor
from app.services.llm.models import DocumentProcessingRequest
from app.utils.utils import create_processed_email_data


class ImageDocumentProcessor(BaseLLMProcessor):
    """Concrete processor for image-based document processing."""
    
    def extract_metadata(self, item: Any, idx: int) -> tuple[str, int, int, str]:
        """Extract metadata from DocumentProcessingRequest for image processing."""
        if not isinstance(item, DocumentProcessingRequest):
            raise ValueError(f"Invalid document data at index {idx}")

        if not item.image_base64:
            raise ValueError(f"No image_base64 provided for item at index {idx}")
        
        # Return metadata info - actual image will be processed separately
        source_id = item.source_id
        user_id = item.user_id
        doc_type = item.document_type
        image_base64 = item.image_base64
        
        # Return image base64 as "text content" - will be used to identify the item
        return image_base64, source_id, user_id, doc_type
    
    def format_accumulated_text(self, idx: int, text_chunk: str, source_id: int, 
                                user_id: int, additional_info: str = "") -> str:
        """Format image metadata with delimiters."""
        return f"\n----image{idx + 1}-start---source_id:\n{source_id}\n---user_id:\n{user_id}\n---document_type:\n{additional_info}\n---image_base64:\n{text_chunk}\n----image{idx + 1}-end----\n"
    
    def save_processed_response(self, processed_data: list[dict]):
        """Save processed image document data to database."""
        try:
            for data in processed_data:
                source_id = data.get("source_id")
                user_id = data.get("user_id")

                # Extract items data before creating the processed data
                items_data = data.pop("items", [])

                data_obj = create_processed_email_data(
                    user_id=user_id,
                    source_id=source_id,
                    email_id=None,  # No email for image uploads
                    data=data
                )
                
                # Save the processed data
                self.db.save_proccessed_email_data(data_obj)
                
                # Save items data if it exists and processed data was saved successfully
                if items_data and data_obj.id:
                    self.db.save_processed_items(data_obj.id, items_data)
                    
        except Exception as e:
            error_msg = f"Error saving image document response: {e}"
            print(error_msg)
            # Re-raise the exception to fail the file processing
            raise Exception(error_msg)
    
    def post_processing(self, results: list[dict]) -> list[dict]:
        """No additional post-processing needed for image uploads."""
        return results
    
    async def process(self, items: list) -> list[dict]:
        """
        Override process method to handle image-based processing.
        Uses multimodal LLM processing instead of text-only.
        Uses async to prevent blocking the event loop.
        """
        try:
            if not items or not isinstance(items, list):
                raise HTTPException(status_code=400, detail="items must be a non-empty list")

            # Collect image data and metadata
            image_items = []
            
            for idx, item in enumerate(items):
                try:
                    if not isinstance(item, DocumentProcessingRequest):
                        raise ValueError(f"Invalid document data at index {idx}")
                    
                    if not item.image_base64:
                        print(f"[WARN] Skipping item index {idx}: No image_base64 provided")
                        continue
                    
                    image_items.append({
                        'idx': idx,
                        'image_base64': item.image_base64,
                        'source_id': item.source_id,
                        'user_id': item.user_id,
                        'document_type': item.document_type
                    })
                    
                except Exception as inner_error:
                    print(f"[WARN] Skipping item index {idx}: {inner_error}")
                    continue

            if not image_items:
                raise HTTPException(status_code=400, detail="No valid image content found to process")

            try:
                # Use async LLM image processing to prevent blocking
                results = await self.llm_service.llm_image_processing(image_items)
            except Exception as llm_error:
                raise HTTPException(status_code=500, detail=f"LLM image processing failed: {llm_error}")

            # Save the processed data
            self.save_processed_response(results)
            
            # Perform any post-processing
            results = self.post_processing(results)

            return results

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error in image process: {e}")
