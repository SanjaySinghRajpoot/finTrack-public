"""
LLM Service Package

This package provides LLM-based document processing capabilities with support for:
- Email batch processing
- Manual document uploads
- Image-based document processing

Main exports:
- LLMService: Main service class for LLM operations
- DocumentProcessingRequest: Pydantic model for document processing requests
- Processors: EmailBatchProcessor, ManualDocumentProcessor, ImageDocumentProcessor
"""

from app.services.llm.service import LLMService
from app.services.llm.models import DocumentProcessingRequest
from app.services.llm.base import BaseLLMProcessor
from app.services.llm.processors import (
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
