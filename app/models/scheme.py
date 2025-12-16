from pydantic import BaseModel
from pydantic import BaseModel, constr, condecimal
from typing import Optional

class TokenRequest(BaseModel):
    access_token: str

class UpdateUserDetailsPayload(BaseModel):
    first_name : Optional[constr(max_length=255)] = None
    last_name : Optional[constr(max_length=255)] = None
    profile_image : Optional[constr(max_length=255)] = None
    country : Optional[constr(max_length=255)] = None
    locale : Optional[constr(max_length=255)] = None

    def to_dict(self) ->  dict:
        result =  {
            "first_name" : self.first_name,
            "last_name" : self.last_name,
            "profile_image" : self.profile_image,
            "country" : self.country,
            "locale" : self.locale
        }
        return result

class ExpenseBase(BaseModel):
    amount: condecimal(gt=0, decimal_places=2)  # amount must be positive
    currency: Optional[constr(max_length=10)] = "USD"
    category: constr(max_length=50)
    description: Optional[constr(max_length=255)] = None

class ExpenseCreate(ExpenseBase):
    is_import: Optional[bool] = None
    processed_data_id: Optional[int] = None
    pass  # Same as base, used for creation

class ExpenseUpdate(BaseModel):
    amount: Optional[condecimal(gt=0, decimal_places=2)] = None
    currency: Optional[constr(max_length=10)] = None
    category: Optional[constr(max_length=50)] = None
    description: Optional[constr(max_length=255)] = None

    def to_dict(self) -> dict:
        data = {
            "amount": self.amount,
            "currency": self.currency,
            "category": self.category,
            "description": self.description
        }

        return data

# Upload Response Models
class UploadSuccessData(BaseModel):
    """Success data for file upload response"""
    success: bool = True
    attachment_id: int
    manual_upload_id: int
    filename: str
    s3_key: str
    file_size: int
    document_type: str

class UploadSuccessResponse(BaseModel):
    """Success response for file upload"""
    message: str
    data: UploadSuccessData

class UploadErrorResponse(BaseModel):
    """Error response for file upload"""
    error: str

# Presigned URL Request/Response Models
class FileUploadRequest(BaseModel):
    """Request model for file upload presigned URL"""
    filename: str
    content_type: str
    file_hash: str
    file_size: int

class PresignedUrlRequest(BaseModel):
    """Request model for batch presigned URL generation"""
    files: list[FileUploadRequest]

class PresignedUrlData(BaseModel):
    """Presigned URL data for a single file"""
    filename: str
    file_hash: str
    presigned_url: Optional[str] = None
    s3_key: Optional[str] = None
    remark: str  # 'success' or 'duplicate'
    duplicate_attachment_id: Optional[int] = None

class PresignedUrlResponse(BaseModel):
    """Response model for presigned URL generation"""
    message: str
    data: list[PresignedUrlData]

# File Metadata Models
class FileMetadata(BaseModel):
    """Metadata for a single uploaded file"""
    filename: str
    file_hash: str
    s3_key: str
    file_size: int
    content_type: str
    document_type: Optional[str] = "INVOICE"
    upload_notes: Optional[str] = None

class FileMetadataRequest(BaseModel):
    """Request model for file metadata after upload"""
    files: list[FileMetadata]

class ProcessedFileData(BaseModel):
    """Response data for processed file metadata"""
    filename: str
    file_hash: str
    attachment_id: int
    manual_upload_id: int
    status: str  # 'created' or 'existing'

class FileMetadataResponse(BaseModel):
    """Response model for file metadata processing"""
    message: str
    data: list[ProcessedFileData]