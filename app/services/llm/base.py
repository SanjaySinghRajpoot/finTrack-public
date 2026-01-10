import asyncio
from abc import ABC, abstractmethod
from typing import Any
from fastapi import HTTPException


class BaseLLMProcessor(ABC):
    """
    Abstract base class for LLM processing.
    Defines the contract for processing different types of documents.
    """
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.db = llm_service.db_service
    
    @abstractmethod
    def extract_metadata(self, item: Any, idx: int) -> tuple[str, int, int, str]:
        """
        Extract text content from the input item.
        
        Args:
            item: Input item (email dict, DocumentProcessingRequest, etc.)
            idx: Index of the item in the batch
            
        Returns:
            Tuple of (text_content, source_id, user_id, additional_info)
        """
        pass
    
    @abstractmethod
    def format_accumulated_text(self, idx: int, text_chunk: str, source_id: int, 
                                user_id: int, additional_info: str = "") -> str:
        """
        Format the text chunk with delimiters for LLM parsing.
        
        Args:
            idx: Index of the item
            text_chunk: Extracted text content
            source_id: Source ID
            user_id: User ID
            additional_info: Any additional information to include
            
        Returns:
            Formatted text string
        """
        pass
    
    @abstractmethod
    def save_processed_response(self, processed_data: list[dict]):
        """
        Save the processed LLM response to the database.
        
        Args:
            processed_data: List of processed data dictionaries
        """
        pass
    
    @abstractmethod
    def post_processing(self, results: list[dict]) -> list[dict]:
        """
        Perform any post-processing after LLM processing.
        
        Args:
            results: LLM processing results
            
        Returns:
            Post-processed results
        """
        pass
    
    async def process(self, items: list) -> list[dict]:
        """
        Main processing pipeline for batch processing items.
        Uses async LLM calls to prevent blocking the event loop.
        
        Args:
            items: List of items to process (emails, documents, etc.)
            
        Returns:
            List of validated JSON objects from the LLM
        """
        try:
            if not items or not isinstance(items, list):
                raise HTTPException(status_code=400, detail="items must be a non-empty list")

            accumulated_text = ""

            for idx, item in enumerate(items):
                try:
                    text_chunk, source_id, user_id, additional_info = self.extract_metadata(item, idx)
                    
                    if not text_chunk:
                        # Skip empty content
                        continue

                    # Format and accumulate text
                    accumulated_text += self.format_accumulated_text(
                        idx, text_chunk, source_id, user_id, additional_info
                    )

                except Exception as inner_error:
                    # Skip this item but continue with others
                    print(f"[WARN] Skipping item index {idx}: {inner_error}")
                    continue

            if not accumulated_text.strip():
                raise HTTPException(status_code=400, detail="No valid content found to process")

            try:
                # Use async LLM processing to prevent blocking
                results = await self.llm_service.llm_processing(accumulated_text)
            except Exception as llm_error:
                raise HTTPException(status_code=500, detail=f"LLM processing failed: {llm_error}")

            # Save the processed data (sync DB operation - runs quickly)
            self.save_processed_response(results)
            
            # Perform any post-processing
            results = self.post_processing(results)

            return results

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error in process: {e}")
