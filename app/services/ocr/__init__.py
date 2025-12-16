"""
OCR Service Package

This package provides OCR-based document processing capabilities using NanoNets API with support for:
- Single document processing
- Batch document processing
- Automatic data validation and standardization
- Fallback to LLM processing if OCR fails

Main exports:
- OCRService: Main service class for OCR operations
- ProcessedDocument: Pydantic model for processed document data
- LineItem: Pydantic model for invoice/bill line items
- DocumentBatchRequest: Request model for batch processing
- DocumentBatchResponse: Response model for batch processing
"""

from app.services.ocr.service import OCRService
from app.services.ocr.models import (
    ProcessedDocument,
    LineItem,
    DocumentMetadata,
    DocumentBatchRequest,
    DocumentBatchResponse,
    NanoNetsAPIResponse,
)

__all__ = [
    "OCRService",
    "ProcessedDocument",
    "LineItem",
    "DocumentMetadata",
    "DocumentBatchRequest",
    "DocumentBatchResponse",
    "NanoNetsAPIResponse",
]
