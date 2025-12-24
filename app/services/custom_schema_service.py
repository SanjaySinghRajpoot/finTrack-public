"""Custom Schema Service Module"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.models import CustomSchema
from app.models.scheme import (
    CustomSchemaCreate, 
    CustomSchemaUpdate, 
    CustomSchemaResponse,
    CustomFieldDefinition,
    DefaultSchemaField,
    FullSchemaResponse
)
from app.repositories.custom_schema_repository import CustomSchemaRepository
from app.utils.exceptions import NotFoundError, DatabaseError


# Default schema fields that are always present in the document schema
DEFAULT_SCHEMA_FIELDS = [
    {"name": "document_type", "label": "Document Type", "type": "string", "required": True, "description": "Type of document (invoice, bill, receipt, etc.)"},
    {"name": "title", "label": "Title", "type": "string", "required": False, "description": "Document title"},
    {"name": "description", "label": "Description", "type": "string", "required": False, "description": "Document description"},
    {"name": "document_number", "label": "Document Number", "type": "string", "required": False, "description": "Invoice/Bill number"},
    {"name": "reference_id", "label": "Reference ID", "type": "string", "required": False, "description": "External reference ID"},
    {"name": "issue_date", "label": "Issue Date", "type": "date", "required": False, "description": "Date document was issued"},
    {"name": "due_date", "label": "Due Date", "type": "date", "required": False, "description": "Payment due date"},
    {"name": "payment_date", "label": "Payment Date", "type": "date", "required": False, "description": "Date payment was made"},
    {"name": "amount", "label": "Amount", "type": "number", "required": False, "description": "Total amount"},
    {"name": "currency", "label": "Currency", "type": "string", "required": False, "description": "Currency code (INR, USD, etc.)"},
    {"name": "is_paid", "label": "Is Paid", "type": "boolean", "required": False, "description": "Whether the document is paid"},
    {"name": "payment_method", "label": "Payment Method", "type": "string", "required": False, "description": "Method of payment"},
    {"name": "vendor_name", "label": "Vendor Name", "type": "string", "required": False, "description": "Name of the vendor/merchant"},
    {"name": "vendor_gstin", "label": "Vendor GSTIN", "type": "string", "required": False, "description": "Vendor's GST identification number"},
    {"name": "category", "label": "Category", "type": "string", "required": False, "description": "Expense category"},
    {"name": "tags", "label": "Tags", "type": "array", "required": False, "description": "Tags for categorization"},
]


class CustomSchemaService:
    """Service class for managing custom document schemas"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = CustomSchemaRepository(db)

    def get_user_schema(self, user_id: int) -> Optional[CustomSchema]:
        """Get custom schema for a user"""
        return self.repository.get_by_user_id(user_id)

    def create_or_update_schema(self, user_id: int, data: CustomSchemaCreate) -> CustomSchema:
        """Create or update custom schema for a user"""
        try:
            schema_data = {
                "fields": [field.model_dump() for field in data.fields],
                "schema_name": data.schema_name,
                "description": data.description,
                "is_active": data.is_active
            }
            return self.repository.create_or_update(user_id, schema_data)
        except Exception as e:
            raise DatabaseError(f"Failed to save custom schema: {str(e)}")

    def update_schema(self, user_id: int, data: CustomSchemaUpdate) -> CustomSchema:
        """Update existing custom schema"""
        existing = self.repository.get_by_user_id(user_id)
        if not existing:
            raise NotFoundError("Custom Schema", str(user_id))
        
        try:
            update_data = {}
            if data.fields is not None:
                update_data["fields"] = [field.model_dump() for field in data.fields]
            if data.schema_name is not None:
                update_data["schema_name"] = data.schema_name
            if data.description is not None:
                update_data["description"] = data.description
            if data.is_active is not None:
                update_data["is_active"] = data.is_active
            
            return self.repository.create_or_update(user_id, update_data)
        except Exception as e:
            raise DatabaseError(f"Failed to update custom schema: {str(e)}")

    def delete_schema(self, user_id: int) -> bool:
        """Delete custom schema for a user"""
        return self.repository.delete_by_user_id(user_id)

    def get_full_schema(self, user_id: int) -> FullSchemaResponse:
        """Get the complete schema including default and custom fields"""
        custom_schema = self.repository.get_by_user_id(user_id)
        
        # Build default fields response
        default_fields = [
            DefaultSchemaField(
                name=field["name"],
                label=field["label"],
                type=field["type"],
                required=field["required"],
                source="default",
                description=field.get("description")
            )
            for field in DEFAULT_SCHEMA_FIELDS
        ]
        
        # Build custom fields response
        custom_fields = []
        schema_name = "Default Schema"
        description = None
        is_active = True
        has_custom_schema = False
        
        if custom_schema and custom_schema.fields:
            has_custom_schema = True
            schema_name = custom_schema.schema_name or "Default Schema"
            description = custom_schema.description
            is_active = custom_schema.is_active
            
            custom_fields = [
                CustomFieldDefinition(**field)
                for field in custom_schema.fields
            ]
        
        return FullSchemaResponse(
            default_fields=default_fields,
            custom_fields=custom_fields,
            schema_name=schema_name,
            description=description,
            is_active=is_active,
            has_custom_schema=has_custom_schema
        )

    def to_response(self, schema: CustomSchema) -> CustomSchemaResponse:
        """Convert CustomSchema model to response schema"""
        return CustomSchemaResponse(
            id=schema.id,
            user_id=schema.user_id,
            fields=[CustomFieldDefinition(**f) for f in (schema.fields or [])],
            schema_name=schema.schema_name,
            description=schema.description,
            is_active=schema.is_active,
            created_at=schema.created_at.isoformat() if schema.created_at else None,
            updated_at=schema.updated_at.isoformat() if schema.updated_at else None
        )
