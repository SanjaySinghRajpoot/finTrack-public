"""
Common schema configurations for document processing.
This schema is used by both OCR service and LLM service.
"""

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
    "metadata": {"type": "array", "description": "List of all relevant document metadata to assist in later processing."},
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
