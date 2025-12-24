from pydantic import BaseModel
from pydantic import BaseModel, constr, condecimal, Field
from typing import Optional, List, Any

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

# Staging Document Models
class StagingDocumentSource(BaseModel):
    """Source information for a staging document"""
    id: int
    type: str
    external_id: Optional[str] = None
    created_at: Optional[str] = None

class StagingDocumentData(BaseModel):
    """Data for a single staging document"""
    id: int
    uuid: str
    filename: str
    file_hash: Optional[str] = None
    s3_key: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    document_type: Optional[str] = None
    source_type: str
    upload_notes: Optional[str] = None
    processing_status: str
    processing_attempts: int
    max_attempts: int
    error_message: Optional[str] = None
    meta_data: Optional[dict] = None
    priority: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    processing_started_at: Optional[str] = None
    processing_completed_at: Optional[str] = None
    source: Optional[StagingDocumentSource] = None

class StagingDocumentsPagination(BaseModel):
    """Pagination info for staging documents"""
    total: int
    limit: int
    offset: int
    has_more: bool

class StagingDocumentsResponse(BaseModel):
    """Response model for staging documents list"""
    data: list[StagingDocumentData]
    pagination: StagingDocumentsPagination


# ================================================================================================
# CUSTOM SCHEMA MODELS
# ================================================================================================

class CustomFieldDefinition(BaseModel):
    """Definition of a single custom field"""
    name: str = Field(..., min_length=1, max_length=100, description="Field identifier (snake_case)")
    label: str = Field(..., min_length=1, max_length=100, description="Display label for the field")
    type: str = Field(..., description="Field type: string, number, date, boolean, select")
    required: bool = Field(default=False, description="Whether the field is required")
    default_value: Optional[Any] = Field(default=None, description="Default value for the field")
    options: Optional[List[str]] = Field(default=None, description="Options for select type fields")
    description: Optional[str] = Field(default=None, max_length=500, description="Field description/help text")
    order: Optional[int] = Field(default=0, description="Display order of the field")


class CustomSchemaCreate(BaseModel):
    """Request model for creating/updating custom schema"""
    fields: List[CustomFieldDefinition] = Field(default_factory=list, description="List of custom field definitions")
    schema_name: Optional[str] = Field(default="Default Schema", max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)


class CustomSchemaUpdate(BaseModel):
    """Request model for updating custom schema"""
    fields: Optional[List[CustomFieldDefinition]] = None
    schema_name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class CustomSchemaResponse(BaseModel):
    """Response model for custom schema"""
    id: int
    user_id: int
    fields: List[CustomFieldDefinition]
    schema_name: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class DefaultSchemaField(BaseModel):
    """Default schema field definition"""
    name: str
    label: str
    type: str
    required: bool
    source: str = "default"  # "default" or "custom"
    description: Optional[str] = None


class FullSchemaResponse(BaseModel):
    """Response model containing both default and custom schema fields"""
    default_fields: List[DefaultSchemaField]
    custom_fields: List[CustomFieldDefinition]
    schema_name: Optional[str]
    description: Optional[str]
    is_active: bool
    has_custom_schema: bool