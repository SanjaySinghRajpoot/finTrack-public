import os
import json
import re
from typing import List, Dict, Any
from openai import OpenAI
from fastapi import HTTPException

from app.services.llm.models import DocumentProcessingRequest
from app.services.llm.processors import (
    EmailBatchProcessor,
    ManualDocumentProcessor,
    ImageDocumentProcessor,
)


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

            # Base prompt template that's shared for all processing types
            self.base_prompt_template = """
                You are given two inputs:
                1. A JSON schema
                2. Multiple {content_type}, each with metadata enclosed between {delimiter_pattern}

                Your task:
                - For each {content_item}:
                - Determine if the {content_description} is relevant to the JSON schema.
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
                - Return the output as a JSON array (one object per {content_item} in the same order as provided).
                - Generate meaningful title if not explicitly available in the document.
                - Follow schema strictly and ensure all required fields for items are populated.
                - Wrap the response in ```json code block.

                JSON Schema:
                {schema}

                {content_label}:
                {content}
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

    def llm_image_processing_batch(self, documents: List[DocumentProcessingRequest]) -> list[dict]:
        """
        Processes image-based document uploads using the LLM service.
        Uses ImageDocumentProcessor to handle the processing pipeline.
        
        Args:
            documents: List of DocumentProcessingRequest objects containing image_base64
            
        Returns:
            List of validated JSON objects from the LLM
        """
        processor = ImageDocumentProcessor(self)
        return processor.process(documents)

    def llm_image_processing(self, image_items: List[Dict[str, Any]]) -> list[dict]:
        """
        Process images using multimodal LLM (vision) capabilities.
        
        Args:
            image_items: List of dicts containing image_base64, source_id, user_id, document_type
            
        Returns:
            List of validated JSON objects from the LLM
        """
        try:
            if not image_items:
                raise HTTPException(status_code=400, detail="No image items provided")

            # Build the prompt for image processing
            image_prompt = self._build_image_prompt(image_items)
            
            # Build multimodal content with images
            multimodal_content = self._build_multimodal_content(image_items, image_prompt)
            
            # Call Gemini API with multimodal content
            response = self._call_gemini_api_with_images(multimodal_content)
            
            # Extract and parse response
            response_text = self._extract_response_text(response)
            parsed_json = self._parse_json_response(response_text)
            validated_data = self._process_and_validate(parsed_json)
            
            return validated_data
            
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error in llm_image_processing: {e}")

    def _build_image_prompt(self, image_items: List[Dict[str, Any]]) -> str:
        """Build prompt for image processing using the unified base template."""
        
        # Build metadata section for images
        metadata_text = ""
        for idx, item in enumerate(image_items):
            metadata_text += f"\n----image{idx + 1}-start---source_id:\n{item['source_id']}\n---user_id:\n{item['user_id']}\n---document_type:\n{item['document_type']}\n----image{idx + 1}-end----\n"
        
        # Use the same base_prompt_template as text processing
        return self.base_prompt_template.format(
            content_type="images of documents",
            delimiter_pattern="---image-start--- and ---image-end---",
            content_item="image",
            content_description="document in the image",
            schema=json.dumps(self.schema, indent=2),
            content_label="Image Metadata",
            content=metadata_text
        )

    def _build_multimodal_content(self, image_items: List[Dict[str, Any]], prompt: str) -> List[Dict[str, Any]]:
        """Build multimodal content array with text and images."""
        content = [{"type": "text", "text": prompt}]
        
        for item in image_items:
            image_base64 = item['image_base64']
            
            try:
                # Add image to content
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                })
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error processing image_base64: {str(e)}")
        
        return content

    def _call_gemini_api_with_images(self, multimodal_content: List[Dict[str, Any]]):
        """Call Gemini API with multimodal content (text + images)."""
        try:
            return self.client.chat.completions.create(
                model="gemini-2.0-flash",
                messages=[
                    {"role": "system", "content": "You are a document analysis AI that extracts structured data from images."},
                    {"role": "user", "content": multimodal_content}
                ],
                temperature=0,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gemini API call with images failed: {str(e)}")

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

    # ------------------ Helper Methods ------------------

    def _validate_texts(self, texts: list[str]):
        if not texts:
            raise HTTPException(status_code=400, detail="No text contents provided")

    def _format_prompt(self, texts: list[str]) -> str:
        """Format prompt for text-based processing using base template."""
        return self.base_prompt_template.format(
            content_type="text contents",
            delimiter_pattern="---text-start--- and ---text-end---",
            content_item="text block",
            content_description="text",
            schema=json.dumps(self.schema, indent=2),
            content_label="Text Contents",
            content=texts
        )

    def _call_gemini_api(self, formatted_prompt: str):
        try:
            return self.client.chat.completions.create(
                model="gemini-2.0-flash",
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
