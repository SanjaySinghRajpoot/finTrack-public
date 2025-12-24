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
from app.services.ocr.models import (
    ProcessedDocument,
    DocumentBatchRequest,
    DocumentBatchResponse,
    NanoNetsAPIResponse,
    LineItem,
)
from app.utils.utils import create_processed_email_data
from app.utils.schema_config import DOCUMENT_SCHEMA, REQUIRED_FIELDS, build_schema_with_custom_fields
from app.utils.json_validator import JSONValidator


class OCRService:
    """
    OCR Service that extracts structured data from documents using NanoNets API.
    Provides methods to process documents from file path and return validated JSON.
    """

    def __init__(self, db: Session, user_id: int, api_key: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
        
        # Build schema with user's custom fields from database
        self.schema = build_schema_with_custom_fields(db, user_id)
        self.validator = JSONValidator(self.schema, REQUIRED_FIELDS)
        
        self.api_key = api_key or settings.NANONETS_API_KEY or settings.DOCSTRANGE_API_KEY
        if self.api_key:
            self.logger.info("OCR Service initialized for NanoNets (API key provided)")
        else:
            self.logger.warning("OCR Service initialized for NanoNets (no API key provided)")

    def is_available(self) -> bool:
        return self.api_key is not None

    def _normalize_document_type(self, doc_type: str) -> str:
        from difflib import get_close_matches
        
        if not doc_type:
            return "other"
        
        # Convert to lowercase and replace spaces/hyphens with underscores
        normalized = doc_type.lower().strip().replace(' ', '_').replace('-', '_')
        
        # Valid document types
        valid_types = [
            'invoice', 'bill', 'emi', 'payment_receipt', 
            'tax_invoice', 'credit_note', 'debit_note', 'other'
        ]
        
        # Try direct match first
        if normalized in valid_types:
            return normalized
        
        # Use fuzzy matching to find the closest match
        matches = get_close_matches(normalized, valid_types, n=1, cutoff=0.6)
        
        if matches:
            return matches[0]
        else:
            return 'other'

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
                # Pass the schema with custom fields as a JSON string to help the extractor align outputs
                "schema": json.dumps(self.schema) if self.schema else None,
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
        """
        Process a single document and return a validated ProcessedDocument model.
        
        Args:
            file_path: Path to the document file
            filename: Name of the file
            source_id: Source identifier
            user_id: User identifier
            document_type: Type of document (default: invoice)
            
        Returns:
            ProcessedDocument model if successful, None otherwise
        """
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
        Extracts data from result.json.content and sets is_processed based on success flag.
        
        Returns:
            Dict ready to be validated by ProcessedDocument model
        """
        from app.repositories.custom_schema_repository import CustomSchemaRepository
        
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
        
        # Check success flag to determine if processing was successful
        is_processing_valid = json_data.get("success", False)
        
        # Extract the actual content from result.json.content
        extracted_content = {}
        if "result" in json_data and isinstance(json_data["result"], dict):
            result = json_data["result"]
            if "json" in result and isinstance(result["json"], dict):
                json_result = result["json"]
                if "content" in json_result and isinstance(json_result["content"], dict):
                    extracted_content = json_result["content"]
        
        # If no content found, return minimal valid structure
        if not extracted_content:
            self.logger.warning("No content found in result.json.content")
            return {
                "source_id": source_id,
                "user_id": user_id,
                "is_processing_valid": is_processing_valid,
                "document_type": document_type,
            }
        
        # Start with all extracted content
        standardized_data = extracted_content.copy()
        
        # Separate custom fields from default fields
        custom_fields_data = {}
        
        # Get custom field definitions from database
        try:
            custom_schema_repo = CustomSchemaRepository(self.db)
            custom_schema = custom_schema_repo.get_by_user_id(user_id)
            
            if custom_schema and custom_schema.is_active and custom_schema.fields:
                # Create a set of custom field names (case-insensitive)
                custom_field_names = {
                    field.get("name", "").lower().replace(' ', '_').replace('-', '_')
                    for field in custom_schema.fields
                    if field.get("name")
                }
                
                # Separate custom fields from standardized data
                for key in list(standardized_data.keys()):
                    normalized_key = key.lower().replace(' ', '_').replace('-', '_')
                    if normalized_key in custom_field_names:
                        # This is a custom field, move it to custom_fields_data
                        custom_fields_data[key] = standardized_data.pop(key)
        except Exception as e:
            self.logger.warning(f"Failed to fetch custom schema: {e}")
        
        # Map common field variations to standard names
        field_mappings = {
            "Invoice Number": "document_number",
            "invoice_number": "document_number",
            "bill_number": "document_number",
            "Document Number": "document_number",
            "Title": "title",
            "document_title": "title",
            "Amount": "amount",
            "Currency": "currency",
            "Description": "description",
            "Issue Date": "issue_date",
            "issue_date": "issue_date",
            "Due Date": "due_date",
            "due_date": "due_date",
            "Payment Date": "payment_date",
            "payment_date": "payment_date",
            "Payment Method": "payment_method",
            "payment_method": "payment_method",
            "Reference ID": "reference_id",
            "reference_id": "reference_id",
            "Vendor Name": "vendor_name",
            "vendor_name": "vendor_name",
            "Vendor GSTIN": "vendor_gstin",
            "vendor_gstin": "vendor_gstin",
            "Document Type": "document_type",
            "document_type": "document_type",
            "Status": "status",
            "status": "status",
        }
        
        # Apply field mappings
        normalized_data = {}
        for key, value in standardized_data.items():
            if key in field_mappings:
                normalized_key = field_mappings[key]
                normalized_data[normalized_key] = value
            else:
                # Keep original key if no mapping found (lowercase with underscores)
                normalized_key = key.lower().replace(' ', '_').replace('-', '_')
                normalized_data[normalized_key] = value
        
        # Handle status -> is_paid conversion
        if "status" in normalized_data:
            status = normalized_data.pop("status")
            status_str = str(status).lower() if status is not None else ""
            if status_str in ["paid", "completed", "success", "true", "1"]:
                normalized_data["is_paid"] = True
            elif status_str in ["unpaid", "pending", "due", "false", "0"]:
                normalized_data["is_paid"] = False
        
        # Normalize document type
        normalized_data["document_type"] = self._normalize_document_type(
            normalized_data.get("document_type", document_type)
        )
        
        # Build metadata
        metadata = {}
        
        # Add custom fields to metadata if any
        if custom_fields_data:
            metadata["custom_fields"] = custom_fields_data
            self.logger.info(f"Stored {len(custom_fields_data)} custom field(s): {list(custom_fields_data.keys())}")
        
        # Store processing metadata from NanoNets response
        if "processing_time" in json_data:
            metadata["processing_time"] = json_data["processing_time"]
        if "record_id" in json_data:
            metadata["record_id"] = json_data["record_id"]
        if "pages_processed" in json_data:
            metadata["pages_processed"] = json_data["pages_processed"]
        
        # Add metadata if it has content
        if metadata:
            normalized_data["metadata"] = metadata
        
        # Add required fields
        normalized_data["source_id"] = source_id
        normalized_data["user_id"] = user_id
        normalized_data["is_processing_valid"] = is_processing_valid
        
        return normalized_data

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
