import os
import json
import re
from abc import ABC, abstractmethod
from openai import OpenAI
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.utils.utils import create_processed_email_data


class DocumentProcessingRequest(BaseModel):
    """
    Flexible Pydantic model for processing different types of documents.
    Can handle emails, manual uploads, or any document type.
    """
    source_id: int
    user_id: int
    document_type: str = "manual_upload"  # email, manual_upload, whatsapp, etc.
    text_content: str
    metadata: Optional[Dict[str, Any]] = {}
    
    class Config:
        extra = "allow"  # Allow additional fields for flexibility


class BaseLLMProcessor(ABC):
    """
    Abstract base class for LLM processing.
    Defines the contract for processing different types of documents.
    """
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.db = llm_service.db
    
    @abstractmethod
    def extract_text_content(self, item: Any, idx: int) -> tuple[str, int, int, str]:
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
    
    def process(self, items: list) -> list[dict]:
        """
        Main processing pipeline for batch processing items.
        
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
                    text_chunk, source_id, user_id, additional_info = self.extract_text_content(item, idx)
                    
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
                results = self.llm_service.llm_processing(accumulated_text)
            except Exception as llm_error:
                raise HTTPException(status_code=500, detail=f"LLM processing failed: {llm_error}")

            # Save the processed data
            self.save_processed_response(results)
            
            # Perform any post-processing
            results = self.post_processing(results)

            return results

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error in process: {e}")


class EmailBatchProcessor(BaseLLMProcessor):
    """Concrete processor for batch email processing."""
    
    def extract_text_content(self, item: Any, idx: int) -> tuple[str, int, int, str]:
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


class ManualDocumentProcessor(BaseLLMProcessor):
    """Concrete processor for manual document uploads."""
    
    def extract_text_content(self, item: Any, idx: int) -> tuple[str, int, int, str]:
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
            print(f"Error saving manual upload response: {e}")
            raise e
    
    def post_processing(self, results: list[dict]) -> list[dict]:
        """No additional post-processing needed for manual uploads."""
        return results


class LLMService:
    """
    LLMService encapsulates the logic for:
      - Interacting with the Gemini API
      - Parsing and validating structured JSON responses
      - Handling multiple text inputs in batches
    """

    def __init__(self, user_id, db):
        try:
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.db = db
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")

            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )

            self.schema = {
                "is_processing_valid": {"type": "boolean", "default": False},
                "source_id": {"type":"integer"},
                "user_id": {"type": "integer"},
                "document_type": {
                    "type": "string",
                    "description": "Type of document",
                    "enum": ["invoice", "bill", "emi", "payment_receipt", "tax_invoice", "credit_note", "debit_note",
                             "other"]
                },
                "title": {"type": "string", "description": "Document title or name"},
                "description": {"type": "string", "description": "Brief description of the document"},
                "document_number": {"type": "string",
                                    "description": "Invoice number, bill number, or document reference number"},
                "reference_id": {"type": "string", "description": "Additional reference ID or order number"},
                "issue_date": {"type": "string", "format": "date",
                               "description": "Date when the document was issued (YYYY-MM-DD)"},
                "due_date": {"type": "string", "format": "date", "description": "Payment due date (YYYY-MM-DD)"},
                "payment_date": {"type": "string", "format": "date",
                                 "description": "Date when payment was made (YYYY-MM-DD)"},
                "amount": {"type": "number", "description": "Total amount of the document"},
                "currency": {"type": "string", "description": "Currency code (default: INR)", "default": "INR"},
                "is_paid": {"type": "boolean", "description": "Whether the document has been paid", "default": False},
                "payment_method": {"type": "string",
                                   "description": "Method of payment (cash, card, bank transfer, etc.)"},
                "vendor_name": {"type": "string", "description": "Name of the vendor or company"},
                "vendor_gstin": {"type": "string", "description": "Vendor's GST identification number"},
                "category": {"type": "string", "description": "Category of expense or document type"},
                "tags": {"type": "array", "items": {"type": "string"},
                         "description": "List of tags for categorization"},
                "metadata": {"type": "array",
                             "description": "List of all relevant document metadata to assist in later processing."},
                "items": {
                    "type": "array",
                    "description": "Array of individual line items from the invoice/bill",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_name": {"type": "string", "description": "Name/description of the product or service"},
                            "item_code": {"type": "string", "description": "Optional product/service code or SKU"},
                            "category": {"type": "string", "description": "Product or service category"},
                            "quantity": {"type": "number", "description": "Quantity of the product/service", "default": 1.0},
                            "unit": {"type": "string", "description": "Unit of measurement (pcs, kg, hr, etc.)"},
                            "rate": {"type": "number", "description": "Rate per unit of the item"},
                            "discount": {"type": "number", "description": "Discount applied on the item", "default": 0.0},
                            "tax_percent": {"type": "number", "description": "Applicable tax percentage"},
                            "total_amount": {"type": "number", "description": "Total amount for the item"},
                            "currency": {"type": "string", "description": "Currency code", "default": "INR"},
                            "meta_data": {"type": "object", "description": "Any additional item-specific data"}
                        },
                        "required": ["item_name", "rate", "total_amount"]
                    }
                }
            }

            self.required_fields = ["title", "amount"]

            self.base_prompt_batch = """
            You are given two inputs:
            1. A JSON schema
            2. Multiple text contents, each enclosed between ---text--start--- and ---text--end---
            
            Your task:
            - For each text block:
              - Determine if the text is relevant to the JSON schema.
              - If irrelevant or incomplete, set `is_processing_valid` to false and leave other fields empty.
              - Otherwise, extract the relevant data and fill the schema.
              - For invoices/bills, MUST extract structured item data into the `items` array with each line item including:
                * item_name (product/service name)
                * quantity (number of units)
                * rate (price per unit)
                * total_amount (total for that line item)
                * tax_percent (if mentioned)
                * unit (measurement unit if specified)
                * discount (if any discount applied)
              - If no line items are clearly visible, leave items array empty.
            - Return the output as a JSON array (one object per text block).
            - Generate meaningful title if not explicitly available in the document.
            - Follow schema strictly and ensure all required fields for items are populated.
            - Wrap the response in ```json code block.
            
            JSON Schema:
            {schema}
            
            Text Contents:
            {texts}
            """

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Initialization error: {str(e)}")

    def llm_batch_processing(self, emails_array: list[dict]) -> list[dict]:
        """
        Processes all emails in a batch using the LLM service.
        Uses EmailBatchProcessor to handle the processing pipeline.
        
        Returns a list of validated JSON objects from the LLM.
        """
        processor = EmailBatchProcessor(self)
        return processor.process(emails_array)

    def llm_manual_processing(self, documents: List[DocumentProcessingRequest]) -> list[dict]:
        """
        Processes manual document uploads using the LLM service.
        Uses ManualDocumentProcessor to handle the processing pipeline.
        
        Args:
            documents: List of DocumentProcessingRequest objects containing document data
            
        Returns:
            List of validated JSON objects from the LLM
        """
        processor = ManualDocumentProcessor(self)
        return processor.process(documents)

    def _validate_json(self, data):
        """Validate a single or list of JSON objects against schema."""
        try:
            if isinstance(data, dict):
                data = [data]

            if not isinstance(data, list):
                raise ValueError("Data must be an array of JSON objects")

            validated_list = []

            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    raise ValueError(f"Item at index {idx} is not a JSON object")

                validated = {}
                for key, rules in self.schema.items():
                    value = item.get(key, rules.get("default"))
                    expected_type = rules["type"]

                    if key in self.required_fields and (value is None or value == ""):
                        raise ValueError(f"Missing required field: {key} in item {idx}")

                    if value is not None:
                        if expected_type == "string" and not isinstance(value, str):
                            raise ValueError(f"Field {key} in item {idx} must be a string")
                        elif expected_type == "number" and not isinstance(value, (int, float)):
                            raise ValueError(f"Field {key} in item {idx} must be a number")
                        elif expected_type == "boolean" and not isinstance(value, bool):
                            raise ValueError(f"Field {key} in item {idx} must be a boolean")
                        elif expected_type == "array":
                            if not isinstance(value, list):
                                raise ValueError(f"Field {key} in item {idx} must be an array")
                            if "items" in rules and rules["items"]["type"] == "string":
                                if not all(isinstance(i, str) for i in value):
                                    raise ValueError(f"All items in {key} (item {idx}) must be strings")

                    validated[key] = value

                extra_keys = set(item.keys()) - set(self.schema.keys())
                if extra_keys:
                    raise ValueError(f"Extra keys not allowed in item {idx}: {extra_keys}")

                validated_list.append(validated)

            return validated_list
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"JSON validation failed: {str(e)}")

    def _build_text_block(self, texts: list[str]) -> str:
        """Builds delimited text block for LLM input."""
        try:
            parts = []
            for i, t in enumerate(texts, start=1):
                parts.append(f"---text{i}-start---\n{t.strip()}\n---text{i}-end---")
            return "\n\n".join(parts)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error while building text block: {str(e)}")

    def llm_processing(self, texts: list[str]) -> list[dict]:
        """
        Orchestrates the full LLM processing pipeline.
        """
        try:
            self._validate_texts(texts)

            formatted_prompt = self._format_prompt(texts)

            response = self._call_gemini_api(formatted_prompt)

            response_text = self._extract_response_text(response)

            parsed_json = self._parse_json_response(response_text)

            validated_data = self._process_and_validate(parsed_json)

            return validated_data

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error in llm_processing: {e}")

        # ------------------ Sub Functions ------------------

    def _validate_texts(self, texts: list[str]):
        if not texts:
            raise HTTPException(status_code=400, detail="No text contents provided")

    def _format_prompt(self, texts: list[str]) -> str:
        return self.base_prompt_batch.format(
            schema=json.dumps(self.schema, indent=2),
            texts=texts
        )

    def _call_gemini_api(self, formatted_prompt: str):
        try:
            return self.client.chat.completions.create(
                model="gemini-2.0-flash-exp",
                messages=[
                    {"role": "system", "content": "You are a JSON parser."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gemini API call failed: {str(e)}")

    def _extract_response_text(self, response):
        if not response.choices or not response.choices[0].message:
            raise HTTPException(status_code=500, detail="No valid response from Gemini")

        return response.choices[0].message.content.strip()

    def _parse_json_response(self, response_text: str):
        json_text = self._extract_json(response_text)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Gemini returned invalid JSON: {e}")

    def _process_and_validate(self, parsed: list[dict]) -> list[dict]:
        all_results = []
        for json_txt in parsed:
            if json_txt["is_processing_valid"]:
                validated = self._validate_json(parsed)
                all_results.extend(validated)
        return all_results

        # ------------------ Existing Utilities ------------------

    def _extract_json(self, response_text: str) -> str:
        """Extract JSON from code blocks."""
        try:
            json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
            match = re.search(json_pattern, response_text, re.DOTALL)
            if match:
                return match.group(1).strip()

            json_pattern_direct = r'\[.*\]'
            match_direct = re.search(json_pattern_direct, response_text, re.DOTALL)
            if match_direct:
                return match_direct.group(0).strip()

            return response_text.strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"JSON extraction failed: {str(e)}")
