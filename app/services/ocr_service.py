"""
OCR Service using NanoNets API for document extraction.
Handles document processing with fallback to LLM if OCR fails.
"""
import logging
import json
import os
import asyncio
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from pydantic import ValidationError

import requests

from app.core.config import settings
from app.services.db_service import DBService
from app.services.ocr_models import (
    ProcessedDocument,
    DocumentBatchRequest,
    DocumentBatchResponse,
    NanoNetsAPIResponse,
    LineItem,
)
from app.utils.utils import create_processed_email_data
from app.utils.schema_config import DOCUMENT_SCHEMA, REQUIRED_FIELDS
from app.utils.json_validator import JSONValidator


class OCRService:

    def __init__(self, db: Session, api_key: Optional[str] = None):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.validator = JSONValidator(DOCUMENT_SCHEMA, REQUIRED_FIELDS)
        self.api_key = api_key or settings.NANONETS_API_KEY or settings.DOCSTRANGE_API_KEY
        if self.api_key:
            self.logger.info("OCR Service initialized for NanoNets (API key provided)")
        else:
            self.logger.warning("OCR Service initialized for NanoNets (no API key provided)")

    def is_available(self) -> bool:
        return self.api_key is not None

    def _call_nanonets_api_sync(self, file_path: str) -> Dict[str, Any]:
        """
        Synchronous NanoNets API call - runs in executor.
        Perform the NanoNets synchronous extraction API call and return parsed JSON.
        Includes schema hint and instructions.
        """
        try:
            url = "https://extraction-api.nanonets.com/api/v1/extract/sync"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            # Build instructions combining caller instructions and schema-based guidance
            data = {
                "output_format": "json",
                # Pass the schema as a JSON string to help the extractor align outputs
                "schema": json.dumps(DOCUMENT_SCHEMA) if DOCUMENT_SCHEMA else None,
            }
            # Remove None values to avoid sending empty fields
            data = {k: v for k, v in data.items() if v is not None}
            # Use requests instead of httpx
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            raise e

    async def _call_nanonets_api(self, file_path: str) -> Dict[str, Any]:
        """
        Async wrapper that runs the synchronous NanoNets API call in an executor
        to prevent blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._call_nanonets_api_sync, file_path)

    async def process_document(
        self,
        file_path: str,
        filename: str,
        source_id: int,
        user_id: int,
        document_type: str = "invoice",
    ) -> Optional[ProcessedDocument]:
        if not self.is_available():
            self.logger.warning("OCR service not available, skipping OCR processing")
            return None
        try:
            self.logger.info(f"Starting OCR processing for {filename}")

            json_data = await self._call_nanonets_api(file_path)
            
            self.logger.debug(f"Raw OCR response: {json_data}")
            
            processed_data = self._enrich_extracted_data(json_data, source_id, user_id, document_type)
            
            # Validate using Pydantic model
            try:
                validated_document = ProcessedDocument(**processed_data)
            except ValidationError as ve:
                self.logger.error(f"Pydantic validation failed for {filename}: {ve}")
                # Fallback to old validator for backward compatibility
                validated_data = self.validator.validate(processed_data, transform_ocr=True)
                if validated_data and len(validated_data) > 0:
                    validated_document = ProcessedDocument(**validated_data[0])
                else:
                    return None
            
            self._save_processed_data(validated_document)
            self.logger.info(f"OCR successfully processed {filename}")
            return validated_document
        except Exception as e:
            self.logger.error(f"OCR processing failed for {filename}: {e}")
            return None

    async def process_document_batch(
        self, 
        documents: List[DocumentBatchRequest]
    ) -> DocumentBatchResponse:
        """
        Process multiple documents in batch.
        
        Args:
            documents: List of DocumentBatchRequest models
            
        Returns:
            DocumentBatchResponse with results and statistics
        """
        results: List[ProcessedDocument] = []
        failed: List[str] = []
        
        for doc in documents:
            # Support both Pydantic models and dicts
            if isinstance(doc, dict):
                doc = DocumentBatchRequest(**doc)
            
            result = await self.process_document(
                file_path=doc.file_path,
                filename=doc.filename,
                source_id=doc.source_id,
                user_id=doc.user_id,
                document_type=doc.document_type,
            )
            if result:
                results.append(result)
            else:
                failed.append(doc.filename)
        
        self.logger.info(f"Batch OCR processing completed: {len(results)}/{len(documents)} successful")
        
        return DocumentBatchResponse(
            successful=len(results),
            total=len(documents),
            results=results,
            failed=failed if failed else None
        )

    def _enrich_extracted_data(
        self,
        json_data: Any,
        source_id: int,
        user_id: int,
        document_type: str,
    ) -> Dict[str, Any]:
        """
        Transform NanoNets API response to standard schema format.
        New format has data in: result.json.content
        
        Returns:
            Dict ready to be validated by ProcessedDocument model
        """
        # Parse string if needed
        if isinstance(json_data, str):
            try:
                json_data = json.loads(json_data)
            except json.JSONDecodeError:
                self.logger.error("Failed to parse JSON string from OCR")
                json_data = {}
        
        # Handle list response (take first item)
        if isinstance(json_data, list) and len(json_data) > 0:
            json_data = json_data[0]
        elif not isinstance(json_data, dict):
            json_data = {}
        
        # Extract the actual content from the new NanoNets format
        # Path: result -> json -> content
        extracted_content = {}
        if "result" in json_data and isinstance(json_data["result"], dict):
            result = json_data["result"]
            if "json" in result and isinstance(result["json"], dict):
                json_result = result["json"]
                if "content" in json_result and isinstance(json_result["content"], dict):
                    extracted_content = json_result["content"]
                else:
                    # Fallback: use the entire json result if no content key
                    extracted_content = json_result
        
        # If no result.json.content found, try old format (structured_data.content)
        if not extracted_content:
            if "structured_data" in json_data and "content" in json_data["structured_data"]:
                extracted_content = json_data["structured_data"]["content"]
            else:
                # Last fallback: use root level data
                extracted_content = json_data.copy()
        
        # Map NanoNets fields to our standard schema
        standardized_data = {}
        
        # Map document_number (could be invoice_number, bill_number, etc.)
        if "invoice_number" in extracted_content:
            standardized_data["document_number"] = extracted_content["invoice_number"]
        elif "bill_number" in extracted_content:
            standardized_data["document_number"] = extracted_content["bill_number"]
        elif "document_number" in extracted_content:
            standardized_data["document_number"] = extracted_content["document_number"]
        
        if "document_title" in extracted_content:
            standardized_data["title"] = extracted_content["document_title"]
        elif "title" in extracted_content:
            standardized_data["title"] = extracted_content["title"]
        
        sender_email = extracted_content.get("sender_email")
        recipient_email = extracted_content.get("recipient_email")
        sender_name = extracted_content.get("sender_name")
        
        status = extracted_content.get("status", "").lower()
        if status in ["paid", "completed", "success"]:
            standardized_data["is_paid"] = True
        elif status in ["unpaid", "pending", "due"]:
            standardized_data["is_paid"] = False
        
        # Direct mappings for common fields
        field_mappings = {
            "amount": "amount",
            "currency": "currency",
            "description": "description",
            "issue_date": "issue_date",
            "due_date": "due_date",
            "payment_date": "payment_date",
            "payment_method": "payment_method",
            "reference_id": "reference_id",
            "vendor_name": "vendor_name",
            "vendor_gstin": "vendor_gstin",
            "category": "category",
            "tags": "tags",
            "items": "items",
        }
        
        for source_field, target_field in field_mappings.items():
            if source_field in extracted_content and extracted_content[source_field] is not None:
                standardized_data[target_field] = extracted_content[source_field]
        
        # Build metadata from extra fields
        metadata = extracted_content.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        
        # Add email fields to metadata if present
        if sender_email:
            metadata["sender_email"] = sender_email
        if recipient_email:
            metadata["recipient_email"] = recipient_email
        if sender_name:
            metadata["sender_name"] = sender_name
        
        # Add API response metadata
        if "confidence_score" in extracted_content:
            metadata["confidence_score"] = extracted_content["confidence_score"]
        if "bounding_boxes" in extracted_content:
            metadata["bounding_boxes"] = extracted_content["bounding_boxes"]
        
        if metadata:
            standardized_data["metadata"] = metadata
        
        # Add required fields
        standardized_data["source_id"] = source_id
        standardized_data["user_id"] = user_id
        standardized_data["is_processing_valid"] = True
        
        # Set document_type (from extracted data or fallback to parameter)
        if "document_type" in extracted_content and extracted_content["document_type"]:
            # Map common variations to our enum values
            doc_type = extracted_content["document_type"].lower().replace(" ", "_")
            if "tax" in doc_type and "invoice" in doc_type:
                standardized_data["document_type"] = "tax_invoice"
            elif "invoice" in doc_type:
                standardized_data["document_type"] = "invoice"
            elif "bill" in doc_type:
                standardized_data["document_type"] = "bill"
            elif "receipt" in doc_type:
                standardized_data["document_type"] = "payment_receipt"
            else:
                standardized_data["document_type"] = document_type
        else:
            standardized_data["document_type"] = document_type
        
        return standardized_data

    def _save_processed_data(self, document: ProcessedDocument):
        """
        Save processed document data to database.
        
        Args:
            document: Validated ProcessedDocument model
        """
        try:
            # Convert Pydantic model to dict for database operations
            data_dict = document.model_dump(exclude_none=False)
            
            source_id = data_dict.get("source_id")
            user_id = data_dict.get("user_id")
            items_data = data_dict.pop("items", [])
            
            # Convert LineItem models to dicts if needed
            if items_data:
                items_data = [
                    item.model_dump() if isinstance(item, LineItem) else item 
                    for item in items_data
                ]
            
            data_obj = create_processed_email_data(
                user_id=user_id,
                source_id=source_id,
                email_id=None,
                data=data_dict,
            )
            db_service = DBService(self.db)
            db_service.save_proccessed_email_data(data_obj)
            if items_data and getattr(data_obj, "id", None):
                db_service.save_processed_items(data_obj.id, items_data)
        except Exception as e:
            self.logger.error(f"Error saving OCR processed data: {e}")
            raise e
