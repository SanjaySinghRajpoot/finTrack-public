"""
Common schema configurations for document processing.
This schema is used by both OCR service and LLM service.
"""

import copy
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session


DOCUMENT_SCHEMA = {
    "is_processing_valid": {"type": "boolean", "default": False},
    "source_id": {"type": "integer"},
    "user_id": {"type": "integer"},
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
    "metadata": {
        "type": "object",
        "description": "Additional document metadata and custom fields",
        "properties": {}
    },
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

# Required fields for validation
REQUIRED_FIELDS = ["amount"]


def build_schema_with_custom_fields(
    db: Session,
    user_id: int,
    base_schema: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build the complete document schema by merging base schema with user's custom fields.
    Custom fields are appended to the metadata section of the schema.
    
    Args:
        db: Database session
        user_id: The user ID to fetch custom fields for
        base_schema: Optional base schema to use (defaults to DOCUMENT_SCHEMA)
        
    Returns:
        Complete document schema with custom fields included in metadata
    """
    from app.repositories.custom_schema_repository import CustomSchemaRepository
    
    # Start with a deep copy of the base schema
    schema = copy.deepcopy(base_schema or DOCUMENT_SCHEMA)
    
    # Fetch custom fields for the user
    try:
        custom_schema_repo = CustomSchemaRepository(db)
        custom_schema = custom_schema_repo.get_by_user_id(user_id)
        
        if not custom_schema or not custom_schema.is_active or not custom_schema.fields:
            return schema
            
        custom_fields = custom_schema.fields
    except Exception:
        # If fetching fails, return base schema
        return schema
    
    # Map custom field types to JSON schema types
    type_mapping = {
        "string": "string",
        "text": "string",
        "number": "number",
        "integer": "integer",
        "date": "string",
        "boolean": "boolean",
        "select": "string",
        "array": "array",
    }
    
    # Build custom fields schema entries
    custom_fields_schema = {}
    for field in custom_fields:
        field_name = field.get("name")
        if not field_name:
            continue
            
        field_type = field.get("type", "string")
        field_label = field.get("label", field_name)
        field_description = field.get("description", f"Custom field: {field_label}")
        field_options = field.get("options")
        field_default = field.get("default_value")
        
        json_type = type_mapping.get(field_type, "string")
        
        field_schema = {
            "type": json_type,
            "description": field_description,
        }
        
        # Add format for date fields
        if field_type == "date":
            field_schema["format"] = "date"
        
        # Add enum for select fields with options
        if field_type == "select" and field_options:
            field_schema["enum"] = field_options
        
        # Add default value if provided
        if field_default is not None:
            field_schema["default"] = field_default
        
        # Add items schema for array type
        if field_type == "array":
            field_schema["items"] = {"type": "string"}
        
        custom_fields_schema[field_name] = field_schema
    
    if not custom_fields_schema:
        return schema
    
    # Append custom fields to the metadata description for LLM/OCR extraction
    # Metadata is an object, so we nest custom fields as properties
    metadata_description = schema.get("metadata", {}).get("description", "")
    schema["metadata"] = {
        "type": "object",
        "description": f"{metadata_description} Custom fields are nested as properties.",
        "properties": custom_fields_schema
    }
    
    return schema
