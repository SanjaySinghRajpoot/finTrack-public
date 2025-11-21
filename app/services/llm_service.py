"""
Backward compatibility wrapper for LLM Service.

This file maintains backward compatibility with existing imports.
The actual implementation has been refactored into the app.services.llm package.

To use the new modular structure, import from:
    from app.services.llm import LLMService, DocumentProcessingRequest
"""

# Re-export everything from the new modular structure
from app.services.llm import (
    LLMService,
    DocumentProcessingRequest,
    BaseLLMProcessor,
    EmailBatchProcessor,
    ManualDocumentProcessor,
    ImageDocumentProcessor,
)

__all__ = [
    "LLMService",
    "DocumentProcessingRequest",
    "BaseLLMProcessor",
    "EmailBatchProcessor",
    "ManualDocumentProcessor",
    "ImageDocumentProcessor",
]
