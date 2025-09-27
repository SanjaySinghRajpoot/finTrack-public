import os
import json
import re
from openai import OpenAI
from fastapi import HTTPException

# Prompt template
base_prompt = """
You are given two inputs:
1. A JSON schema
2. A text content

Your task:
- Extract relevant information from the text.
- Populate the JSON schema with the extracted values.
- Make sure the output strictly follows the JSON structure.
- Do not add any extra keys, and keep values empty if they cannot be found in the text.
- Return a valid JSON object wrapped inside a json code block.

JSON Schema:
{schema}

Text Content:
{text}

Return ONLY the populated JSON object wrapped in ```json code block.
"""

# Schema definition
schema = {
    "document_type": {
        "type": "string",
        "description": "Type of document",
        "enum": ["invoice", "bill", "emi", "payment_receipt", "tax_invoice", "credit_note", "debit_note", "other"]
    },
    "title": {"type": "string", "description": "Document title or name"},
    "description": {"type": "string", "description": "Brief description of the document"},
    "document_number": {"type": "string", "description": "Invoice number, bill number, or document reference number"},
    "reference_id": {"type": "string", "description": "Additional reference ID or order number"},
    "issue_date": {"type": "string", "format": "date", "description": "Date when the document was issued (YYYY-MM-DD)"},
    "due_date": {"type": "string", "format": "date", "description": "Payment due date (YYYY-MM-DD)"},
    "payment_date": {"type": "string", "format": "date", "description": "Date when payment was made (YYYY-MM-DD)"},
    "amount": {"type": "number", "description": "Total amount of the document"},
    "currency": {"type": "string", "description": "Currency code (default: INR)", "default": "INR"},
    "is_paid": {"type": "boolean", "description": "Whether the document has been paid", "default": False},
    "payment_method": {"type": "string", "description": "Method of payment (cash, card, bank transfer, etc.)"},
    "vendor_name": {"type": "string", "description": "Name of the vendor or company"},
    "vendor_gstin": {"type": "string", "description": "Vendor's GST identification number"},
    "category": {"type": "string", "description": "Category of expense or document type"},
    "tags": {"type": "array", "items": {"type": "string"}, "description": "List of tags for categorization"},
}

# Required fields
required_fields = ["title", "amount"]


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from a response that contains JSON wrapped in code blocks.
    Supports both ```json and ``` code blocks.
    """
    # Pattern to match ```json ... ``` or ``` ... ``` blocks
    json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    
    # Search for JSON block
    match = re.search(json_pattern, response_text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # If no code block found, try to extract JSON directly
    # Look for content between { and }
    json_pattern_direct = r'\{.*\}'
    match_direct = re.search(json_pattern_direct, response_text, re.DOTALL)
    
    if match_direct:
        return match_direct.group(0).strip()
    
    # If still no match, return the original text
    return response_text.strip()


def validate_json(data: dict, schema: dict, required: list) -> dict:
    """
    Validate and clean JSON data against schema.
    """
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Data must be a JSON object")

    validated = {}

    for key, rules in schema.items():
        if key in required and key not in data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {key}")

        value = data.get(key, rules.get("default"))

        if value is not None:
            expected_type = rules["type"]
            if expected_type == "string" and not isinstance(value, str):
                raise HTTPException(status_code=400, detail=f"Field {key} must be a string")
            elif expected_type == "number" and not isinstance(value, (int, float)):
                raise HTTPException(status_code=400, detail=f"Field {key} must be a number")
            elif expected_type == "boolean" and not isinstance(value, bool):
                raise HTTPException(status_code=400, detail=f"Field {key} must be a boolean")
            elif expected_type == "array":
                if not isinstance(value, list):
                    raise HTTPException(status_code=400, detail=f"Field {key} must be an array")
                if "items" in rules and rules["items"]["type"] == "string":
                    if not all(isinstance(i, str) for i in value):
                        raise HTTPException(status_code=400, detail=f"All items in {key} must be strings")

            if "enum" in rules and value not in rules["enum"]:
                raise HTTPException(status_code=400, detail=f"Invalid value for {key}. Allowed: {rules['enum']}")

        validated[key] = value

    extra_keys = set(data.keys()) - set(schema.keys())
    if extra_keys:
        raise HTTPException(status_code=400, detail=f"Extra keys not allowed: {extra_keys}")

    return validated


class LLMService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

    def get_schema(self) -> dict:
        return schema

    def call_gemini(self, text_content: str) -> dict:
        """
        Calls Gemini API with the given text content,
        extracts JSON from code block response, and validates against schema.
        """
        formatted_prompt = base_prompt.format(
            schema=json.dumps(schema, indent=2),
            text=text_content
        )

        try:
            response = self.client.chat.completions.create(
                model="gemini-2.0-flash-exp",  
                messages=[
                    {"role": "system", "content": "You are a JSON parser."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0,
            )

            if not response.choices or not response.choices[0].message:
                raise HTTPException(status_code=500, detail="No response from Gemini")

            response_text = response.choices[0].message.content.strip()

            # Extract JSON from code block
            json_text = extract_json_from_response(response_text)

            try:
                response_json = json.loads(json_text)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=500, detail=f"Gemini did not return valid JSON: {e}")

            validated_json = validate_json(response_json, schema, required_fields)
            return validated_json

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini API request failed: {e}")