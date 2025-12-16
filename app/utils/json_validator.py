"""
JSON validation utility for document processing.
Provides schema validation for OCR and LLM extracted data.
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import HTTPException


class OCRResponseTransformer:
    """
    Transforms OCR response format to standardized schema format.
    Handles the nested structure from docstrange OCR output.
    """
    
    @staticmethod
    def transform(ocr_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform OCR response to standardized format.
        
        Args:
            ocr_response: Raw OCR response with nested structure
            
        Returns:
            Flattened, standardized dictionary
        """
        if not ocr_response:
            return {}
        
        if 'structured_data' in ocr_response and 'content' in ocr_response['structured_data']:
            content = ocr_response['structured_data']['content']
        else:
            content = ocr_response
        
        standardized = {}
        
        for key, value in content.items():
            if key == 'items' and isinstance(value, list):
                standardized['items'] = OCRResponseTransformer._transform_items(value)
            elif key == 'metadata' and isinstance(value, list):
                standardized['metadata'] = value
            else:
                standardized[key] = value
        
        if 'is_processing_valid' not in standardized:
            standardized['is_processing_valid'] = ocr_response.get('is_processing_valid', True)
        
        top_level_fields = ['source_id', 'user_id', 'document_type', 'format', 'is_processing_valid']
        for field in top_level_fields:
            if field in ocr_response and field not in standardized:
                standardized[field] = ocr_response[field]
        
        return standardized
    
    @staticmethod
    def _transform_items(items: List[Any]) -> List[Dict[str, Any]]:
        """Transform line items if they exist."""
        if not items:
            return []
        
        transformed_items = []
        for item in items:
            if isinstance(item, dict):
                transformed_items.append(item)
        
        return transformed_items


class JSONValidator:
    """
    Validates JSON data against a predefined schema.
    Can be used by OCR service, LLM service, or any other service.
    """
    
    def __init__(self, schema: Dict[str, Any], required_fields: Optional[List[str]] = None):
        """
        Initialize the JSON validator.
        
        Args:
            schema: JSON schema to validate against
            required_fields: List of required field names
        """
        self.schema = schema
        self.required_fields = required_fields or []
        self.logger = logging.getLogger(__name__)
        self.transformer = OCRResponseTransformer()
    
    def validate(self, data: Any, transform_ocr: bool = False) -> List[Dict[str, Any]]:
        """
        Validate a single or list of JSON objects against schema.
        
        Args:
            data: Single dict or list of dicts to validate
            transform_ocr: Whether to transform OCR response format first
            
        Returns:
            List of validated JSON objects
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            if isinstance(data, dict):
                data = [data]
            
            if not isinstance(data, list):
                raise ValueError("Data must be an array of JSON objects")
            
            validated_list = []
            
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    raise ValueError(f"Item at index {idx} is not a JSON object")
                
                if transform_ocr:
                    item = self.transformer.transform(item)
                
                validated = self._validate_item(item, idx)
                validated_list.append(validated)
            
            return validated_list
            
        except Exception as e:
            self.logger.error(f"JSON validation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"JSON validation failed: {str(e)}")
    
    def _validate_item(self, item: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """
        Validate a single item against schema.
        
        Args:
            item: Dictionary to validate
            idx: Index of item in the array (for error reporting)
            
        Returns:
            Validated dictionary
        """
        validated = {}
        
        for key, rules in self.schema.items():
            value = item.get(key, rules.get("default"))
            expected_type = rules["type"]
            
            if key in self.required_fields and (value is None or value == ""):
                raise ValueError(f"Missing required field: {key} in item {idx}")
            
            if value is not None:
                self._validate_type(key, value, expected_type, rules, idx)
            
            validated[key] = value
        
        extra_keys = set(item.keys()) - set(self.schema.keys())
        if extra_keys:
            self.logger.warning(f"Extra keys not in schema for item {idx}: {extra_keys}")
        
        return validated
    
    def _validate_type(self, key: str, value: Any, expected_type: str, rules: Dict[str, Any], idx: int):
        """
        Validate the type of a value.
        
        Args:
            key: Field name
            value: Value to validate
            expected_type: Expected type string
            rules: Schema rules for the field
            idx: Item index for error reporting
        """
        if expected_type == "string" and not isinstance(value, str):
            raise ValueError(f"Field {key} in item {idx} must be a string")
        elif expected_type == "number" and not isinstance(value, (int, float)):
            raise ValueError(f"Field {key} in item {idx} must be a number")
        elif expected_type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"Field {key} in item {idx} must be a boolean")
        elif expected_type == "array":
            if not isinstance(value, list):
                raise ValueError(f"Field {key} in item {idx} must be an array")
            if "items" in rules:
                self._validate_array_items(key, value, rules["items"], idx)
    
    def _validate_array_items(self, key: str, array: List[Any], item_rules: Dict[str, Any], idx: int):
        """
        Validate items in an array.
        
        Args:
            key: Field name
            array: Array to validate
            item_rules: Rules for array items
            idx: Item index for error reporting
        """
        item_type = item_rules.get("type")
        
        if item_type == "string":
            if not all(isinstance(i, str) for i in array):
                raise ValueError(f"All items in {key} (item {idx}) must be strings")
        elif item_type == "object":
            for arr_idx, obj in enumerate(array):
                if not isinstance(obj, dict):
                    raise ValueError(f"Item {arr_idx} in {key} (item {idx}) must be an object")
                if "properties" in item_rules:
                    self._validate_nested_object(key, obj, item_rules["properties"], arr_idx, idx)
    
    def _validate_nested_object(self, key: str, obj: Dict[str, Any], properties: Dict[str, Any], 
                                arr_idx: int, parent_idx: int):
        """
        Validate nested object properties.
        
        Args:
            key: Parent field name
            obj: Object to validate
            properties: Property schema
            arr_idx: Index in the array
            parent_idx: Parent item index
        """
        required = properties.get("required", [])
        
        for prop_key, prop_rules in properties.items():
            if prop_key == "required":
                continue
            
            value = obj.get(prop_key)
            
            if prop_key in required and (value is None or value == ""):
                raise ValueError(
                    f"Missing required field '{prop_key}' in {key}[{arr_idx}] (item {parent_idx})"
                )
