import asyncio
import json
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI
from fastapi import HTTPException

from app.core.config import settings
from app.services.db_service import DBService
from app.services.llm.models import DocumentProcessingRequest
from app.services.llm.processors import (
    EmailBatchProcessor,
    ManualDocumentProcessor,
    ImageDocumentProcessor,
)
from app.utils.schema_config import DOCUMENT_SCHEMA, REQUIRED_FIELDS, build_schema_with_custom_fields
from app.utils.json_validator import JSONValidator


class LLMService:

    def __init__(self, user_id: int, db_service: DBService):
        try:
            self.api_key = settings.OPENAI_API_KEY
            self.db_service = db_service
            self.user_id = user_id
            self.model = settings.LLM_MODEL  
            
            if not self.api_key and "localhost" not in settings.OPENAI_BASE_URL:
                raise ValueError("OPENAI_API_KEY environment variable is not set")

            self.client = OpenAI(
                api_key=self.api_key,
                base_url=settings.OPENAI_BASE_URL
            )

            self.schema = build_schema_with_custom_fields(db_service.db, user_id)
            self.required_fields = REQUIRED_FIELDS
            self.validator = JSONValidator(self.schema, self.required_fields)

            self.base_prompt_template = """
                You are given two inputs:
                1. A JSON schema
                2. Multiple {content_type}, each with metadata enclosed between {delimiter_pattern}

                Your task:
                - For each {content_item}:
                - Determine if the {content_description} is relevant to the JSON schema.
                - If irrelevant or incomplete, set `is_processing_valid` to false and provide a concise error message in the `description` field. populate source_id and Leave other fields empty other 
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

    async def llm_batch_processing(self, emails_array: list[dict]) -> list[dict]:
        processor = EmailBatchProcessor(self)
        return await processor.process(emails_array)

    async def llm_manual_processing(self, documents: List[DocumentProcessingRequest]) -> list[dict]:
        processor = ManualDocumentProcessor(self)
        return await processor.process(documents)

    async def llm_image_processing_batch(self, documents: List[DocumentProcessingRequest]) -> list[dict]:
        processor = ImageDocumentProcessor(self)
        return await processor.process(documents)

    async def llm_image_processing(self, image_items: List[Dict[str, Any]]) -> list[dict]:
        try:
            if not image_items:
                raise HTTPException(status_code=400, detail="No image items provided")

            image_prompt = self._build_image_prompt(image_items)
            multimodal_content = self._build_multimodal_content(image_items, image_prompt)
            response = await self._call_gemini_api_with_images_async(multimodal_content)
            response_text = self._extract_response_text(response)
            parsed_json = self._parse_json_response(response_text)
            validated_data = self._process_and_validate(parsed_json)
            
            return validated_data
            
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error in llm_image_processing: {e}")

    def _build_image_prompt(self, image_items: List[Dict[str, Any]]) -> str:
        metadata_text = ""
        for idx, item in enumerate(image_items):
            metadata_text += f"\n----image{idx + 1}-start---source_id:\n{item['source_id']}\n---user_id:\n{item['user_id']}\n---document_type:\n{item['document_type']}\n----image{idx + 1}-end----\n"
        
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
        content = [{"type": "text", "text": prompt}]
        
        for item in image_items:
            image_base64 = item['image_base64']
            
            try:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                })
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error processing image_base64: {str(e)}")
        
        return content

    def _call_gemini_api_with_images(self, multimodal_content: List[Dict[str, Any]]):
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a document analysis AI that extracts structured data from images."},
                    {"role": "user", "content": multimodal_content}
                ],
                temperature=0,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gemini API call with images failed: {str(e)}")

    async def _call_gemini_api_with_images_async(self, multimodal_content: List[Dict[str, Any]]):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._call_gemini_api_with_images,
            multimodal_content
        )

    def _validate_json(self, data):
        return self.validator.validate(data)

    async def llm_processing(self, texts: list[str]) -> list[dict]:
        try:
            self._validate_texts(texts)
            formatted_prompt = self._format_prompt(texts)
            response = await self._call_gemini_api_async(formatted_prompt)
            response_text = self._extract_response_text(response)
            parsed_json = self._parse_json_response(response_text)
            validated_data = self._process_and_validate(parsed_json)

            return validated_data

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error in llm_processing: {e}")

    def _validate_texts(self, texts: list[str]):
        if not texts:
            raise HTTPException(status_code=400, detail="No text contents provided")

    def _format_prompt(self, texts: list[str]) -> str:
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
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a JSON parser."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gemini API call failed: {str(e)}")

    async def _call_gemini_api_async(self, formatted_prompt: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._call_gemini_api,
            formatted_prompt
        )

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
        
        for json_data in parsed:
            result = self._process_single_document(json_data)
            if result:
                all_results.append(result)
        
        return all_results
    
    def _process_single_document(self, json_data: dict) -> Optional[dict]:
        source_id = json_data.get("source_id")
        if not source_id:
            return None
        
        if not json_data.get("is_processing_valid", False):
            self._handle_invalid_document(source_id, json_data)
            return None
        
        return self._validate_against_schema(source_id, json_data)
    
    def _handle_invalid_document(
        self, 
        source_id: int, 
        json_data: dict
    ) -> None:
        error_message = json_data.get(
            "description", 
            "LLM processing failed: Document content is invalid or irrelevant to the schema."
        )
        
        self._update_staging_status_failed(
            source_id=source_id,
            error_message=error_message,
            error_type="LLMValidationError",
            metadata={"validation_result": "is_processing_valid=false"}
        )
    
    def _validate_against_schema(
        self, 
        source_id: int, 
        json_data: dict
    ) -> Optional[dict]:
        try:
            validated = self._validate_json([json_data])
            
            if validated:
                return validated[0] if validated else None
            else:
                self._update_staging_status_failed(
                    source_id=source_id,
                    error_message="LLM processing returned valid=true but data failed schema validation.",
                    error_type="SchemaValidationError",
                    metadata={"validation_result": "schema_validation_failed"}
                )
                return None
                
        except Exception as e:
            self._update_staging_status_failed(
                source_id=source_id,
                error_message=f"Schema validation error: {str(e)}",
                error_type="ValidationException",
                metadata={"exception": type(e).__name__}
            )
            return None
    
    def _update_staging_status_failed(
        self,
        source_id: int,
        error_message: str,
        error_type: str,
        metadata: dict
    ) -> None:
        try:
            # Use the db_service instance passed during initialization
            self.db_service.update_staging_status_with_source_id(
                source_id=source_id,
                status="failed",
                error_message=error_message,
                metadata={
                    "error_type": error_type,
                    **metadata
                }
            )
        except Exception as update_error:
            print(f"Error updating staging status for source_id {source_id}: {str(update_error)}")

    def _extract_json(self, response_text: str) -> str:
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
