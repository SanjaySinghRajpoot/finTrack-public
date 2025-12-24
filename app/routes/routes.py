from requests import Session
from starlette.responses import JSONResponse

from app.db_config import SessionLocal
from app.middleware.auth_middleware import jwt_middleware
from app.models.scheme import (
    TokenRequest, ExpenseCreate, ExpenseUpdate, UpdateUserDetailsPayload,
    PresignedUrlRequest, FileMetadataRequest, StagingDocumentsResponse,
    CustomSchemaCreate, CustomSchemaUpdate, FullSchemaResponse
)
from fastapi import APIRouter, Request, Depends, UploadFile, File, Query
from app.controller import (
    EmailController,
    ProcessedDataController,
    AuthController,
    ExpenseController,
    FileController,
    UserController,
    IntegrationController,
    CustomSchemaController
)
from app.services.s3_service import S3Service

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------- AUTH ROUTES -----------
@router.get("/login")
async def login():
    return await AuthController.login()


@router.get("/emails/oauth2callback")
async def oauth2callback(request: Request, code: str, db: Session = Depends(get_db)):
    return await AuthController.oauth2callback(request, code, db)


# ----------- EMAIL ROUTES -----------
@router.post("/emails")
async def get_emails(
    payload: TokenRequest,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    return await EmailController.get_emails(payload, user, db)


# ----------- USER ROUTES -----------
@router.get("/user")
async def get_user(
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    return await UserController.get_user_info(user, db)

@router.put("/user")
async def update_user(
    payload: UpdateUserDetailsPayload,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):

    return await UserController.update_user_details(user, payload.to_dict(), db)


@router.get("/user/settings")
async def get_user(
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    return await UserController.get_user_settings(user, db)


# ----------- Processed Data ROUTES -----------
@router.get("/processed-expense/info")
async def get_payment_info(user=Depends(jwt_middleware),
                     db: Session = Depends(get_db),
                     limit: int = Query(10, ge=1, le=100, description="Number of records per page"),
                     offset: int = Query(0, ge=0, description="Number of records to skip"),
                     ):
    return await ProcessedDataController.get_payment_info(user, db, limit, offset)


@router.get("/staging-documents", response_model=StagingDocumentsResponse)
async def get_staging_documents(
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Number of records per page"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    status: str = Query(None, description="Filter by processing status (pending, in_progress, completed, failed)")
):
    """
    Get paginated list of staging documents for the authenticated user.
    These are documents that are queued or being processed.
    """
    return await ProcessedDataController.get_staging_documents(user, db, limit, offset, status)


# ----------- EXPENSE ROUTES -----------
@router.post("/expense")
async def create_expense(payload: ExpenseCreate, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return await ExpenseController.create_expense(payload, user, db)

@router.get("/expense")
async def list_expenses(user=Depends(jwt_middleware),
                  db: Session = Depends(get_db),
                  limit: int = Query(10, ge=1, le=100, description="Number of records per page"),
                  offset: int = Query(0, ge=0, description="Number of records to skip")):
    return await ExpenseController.list_expenses(user, db, limit, offset)


@router.get("/expense/{expense_uuid}")
async def get_expense(expense_uuid: str, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return await ExpenseController.get_expense(expense_uuid, user, db)


@router.put("/expense/{expense_uuid}")
async def update_expense(expense_uuid: str, payload: ExpenseUpdate, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return await ExpenseController.update_expense(expense_uuid, payload, user, db)


@router.delete("/expense/{expense_uuid}")
async def delete_expense(expense_uuid: str, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return await ExpenseController.delete_expense(expense_uuid, user, db)

# -------- S3 ROUTES ---------------
@router.get("/attachment/view")
async def view_pdf(s3_url: str, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return await FileController.get_attachment_signed_url(s3_url=s3_url, db=db)

@router.post("/files/presigned-urls")
async def get_presigned_upload_urls(
    payload: PresignedUrlRequest,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """
    Get presigned URLs for direct S3 upload.
    Checks for duplicate files by hash before generating URLs.
    """
    return await FileController.get_presigned_upload_urls(payload, user, db)

@router.post("/files/metadata")
async def process_uploaded_files(
    payload: FileMetadataRequest,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """
    Process metadata for files uploaded directly to S3.
    Creates attachment and manual_upload entries.
    """
    return await FileController.process_uploaded_files_metadata(**{
        "payload": payload,
        "user": user,
        "db": db
    })

@router.post("/upload")
async def upload_file_route(
    file: UploadFile = File(...),
    document_type: str = "INVOICE",
    upload_notes: str = None,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """Upload a PDF file and create entries in ManualUpload and Attachment tables."""
    return await FileController.upload_file(**{
        "file": file,
        "user": user,
        "db": db,
        "document_type": document_type,
        "upload_notes": upload_notes
    })


# -------- INTEGRATION ROUTES ---------------
@router.get("/integration/{slug}/link")
async def link_integration(
    slug: str,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """
    Initiate linking for an integration (e.g., Gmail).
    Returns OAuth URL or integration-specific instructions.
    """
    return await IntegrationController.link_integration(slug, user, db)


@router.get("/integration/{slug}/callback")
async def integration_callback(
    slug: str,
    code: str,
    state: str = None,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback for integration (public endpoint - no auth required).
    Completes the integration linking process and redirects to frontend.
    """
    return await IntegrationController.oauth_callback(slug, code, state, db)


@router.delete("/integration/{slug}/delink")
async def delink_integration(
    slug: str,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """
    Delink/disconnect an integration.
    Removes tokens and integration configuration.
    """
    return await IntegrationController.delink_integration(slug, user, db)


# ----------- CUSTOM SCHEMA ROUTES -----------
@router.get("/schema", response_model=FullSchemaResponse)
async def get_document_schema(
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """
    Get the full document schema including default and custom fields.
    This endpoint returns all available columns/fields that can be displayed in tables.
    """
    return await CustomSchemaController.get_schema(user, db)


@router.post("/schema/custom")
async def save_custom_schema(
    payload: CustomSchemaCreate,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """
    Create or update custom schema fields for the authenticated user.
    Custom fields will be added to the default schema fields.
    """
    return await CustomSchemaController.save_custom_schema(payload, user, db)


@router.put("/schema/custom")
async def update_custom_schema(
    payload: CustomSchemaUpdate,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """
    Update existing custom schema fields.
    Only provided fields will be updated.
    """
    return await CustomSchemaController.update_custom_schema(payload, user, db)


@router.delete("/schema/custom")
async def delete_custom_schema(
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """
    Delete custom schema fields for the authenticated user.
    This will reset to using only the default schema fields.
    """
    return await CustomSchemaController.delete_custom_schema(user, db)
