from pydantic import BaseModel
from typing import Optional, Dict, Any


class DocumentProcessingRequest(BaseModel):
    """
    Flexible Pydantic model for processing different types of documents.
    Can handle emails, manual uploads, or any document type.
    """
    source_id: int
    user_id: int
    document_type: str = "manual_upload"  # email, manual_upload, whatsapp, etc.
    text_content: Optional[str] = None
    image_base64: Optional[str] = None  # Base64 encoded image for image-based processing
    metadata: Optional[Dict[str, Any]] = {}
    
    class Config:
        extra = "allow"  # Allow additional fields for flexibility
