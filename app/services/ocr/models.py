"""
Pydantic models for OCR Service.
Ensures consistent data structure and validation for OCR processing.
"""
from typing import Optional, List, Dict, Any, Literal
from datetime import date
from pydantic import BaseModel, Field, field_validator, ConfigDict


class LineItem(BaseModel):
    """Line item from invoice/bill"""
    item_name: str = Field(..., description="Name/description of the product or service")
    item_code: Optional[str] = Field(None, description="Product/service code or SKU")
    category: Optional[str] = Field(None, description="Product or service category")
    quantity: float = Field(default=1.0, description="Quantity of the product/service")
    unit: Optional[str] = Field(None, description="Unit of measurement (pcs, kg, hr, etc.)")
    rate: float = Field(..., description="Rate per unit of the item")
    discount: float = Field(default=0.0, description="Discount applied on the item")
    tax_percent: Optional[float] = Field(None, description="Applicable tax percentage")
    total_amount: float = Field(..., description="Total amount for the item")
    currency: str = Field(default="INR", description="Currency code")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Additional item-specific data")

    model_config = ConfigDict(extra="allow")


class DocumentMetadata(BaseModel):
    """Metadata for processed document"""
    sender_email: Optional[str] = None
    recipient_email: Optional[str] = None
    sender_name: Optional[str] = None
    confidence_score: Optional[float] = None
    bounding_boxes: Optional[List[Dict[str, Any]]] = None
    
    model_config = ConfigDict(extra="allow")


class ProcessedDocument(BaseModel):
    """Main document structure from OCR processing"""
    # Required fields
    source_id: int = Field(..., description="Source identifier")
    user_id: int = Field(..., description="User identifier")
    amount: float = Field(..., description="Total amount of the document")
    
    # Processing metadata
    is_processing_valid: bool = Field(default=True, description="Whether processing was valid")
    
    # Document type and identification
    document_type: Literal[
        "invoice", "bill", "emi", "payment_receipt", 
        "tax_invoice", "credit_note", "debit_note", "other"
    ] = Field(default="invoice", description="Type of document")
    
    title: Optional[str] = Field(None, description="Document title or name")
    description: Optional[str] = Field(None, description="Brief description of the document")
    document_number: Optional[str] = Field(None, description="Invoice/bill/document reference number")
    reference_id: Optional[str] = Field(None, description="Additional reference ID or order number")
    
    # Dates
    issue_date: Optional[str] = Field(None, description="Document issue date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Payment due date (YYYY-MM-DD)")
    payment_date: Optional[str] = Field(None, description="Payment date (YYYY-MM-DD)")
    
    # Financial details
    currency: str = Field(default="INR", description="Currency code")
    is_paid: bool = Field(default=False, description="Whether the document has been paid")
    payment_method: Optional[str] = Field(None, description="Method of payment")
    
    # Vendor information
    vendor_name: Optional[str] = Field(None, description="Name of the vendor or company")
    vendor_gstin: Optional[str] = Field(None, description="Vendor's GST identification number")
    
    # Categorization
    category: Optional[str] = Field(None, description="Category of expense or document type")
    tags: Optional[List[str]] = Field(None, description="List of tags for categorization")
    
    # Additional data
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    items: Optional[List[LineItem]] = Field(None, description="Line items from the invoice/bill")
    
    model_config = ConfigDict(extra="allow")

    @field_validator('items', mode='before')
    @classmethod
    def validate_items(cls, v):
        """Convert dict items to LineItem objects"""
        if v is None:
            return None
        if isinstance(v, list):
            return [LineItem(**item) if isinstance(item, dict) else item for item in v]
        return v
    
    @field_validator('metadata', mode='before')
    @classmethod
    def validate_metadata(cls, v):
        """Ensure metadata is a dict or None"""
        if v is None or isinstance(v, dict):
            return v
        return {}


class NanoNetsAPIResponse(BaseModel):
    """Response structure from NanoNets API"""
    result: Optional[Dict[str, Any]] = None
    structured_data: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(extra="allow")


class DocumentBatchRequest(BaseModel):
    """Request model for batch document processing"""
    file_path: str
    filename: str
    source_id: int
    user_id: int
    document_type: str = "invoice"


class DocumentBatchResponse(BaseModel):
    """Response model for batch document processing"""
    successful: int
    total: int
    results: List[ProcessedDocument]
    failed: Optional[List[str]] = None
