from requests import Session
from starlette.responses import JSONResponse

from app.db_config import SessionLocal
from app.middleware.auth_middleware import jwt_middleware
from app.models.scheme import TokenRequest, ExpenseCreate, ExpenseUpdate, UpdateUserDetailsPayload
from fastapi import APIRouter, Request, Depends, UploadFile, File, Query
from app.controller.controller import EmailController, ProcessedDataController, AuthController, ExpenseController, \
    FileController, UserController
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
def login():
    return AuthController.login()


@router.get("/emails/oauth2callback")
def oauth2callback(request: Request, code: str, db: Session = Depends(get_db)):
    return AuthController.oauth2callback(request, code, db)


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
def get_payment_info(user=Depends(jwt_middleware),
                     db: Session = Depends(get_db),
                     limit: int = Query(10, ge=1, le=100, description="Number of records per page"),
                     offset: int = Query(0, ge=0, description="Number of records to skip"),
                     ):
    return ProcessedDataController.get_payment_info(user, db, limit, offset)


# ----------- EXPENSE ROUTES -----------
@router.post("/expense")
def create_expense(payload: ExpenseCreate, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return ExpenseController.create_expense(payload, user, db)

@router.get("/expense")
def list_expenses(user=Depends(jwt_middleware),
                  db: Session = Depends(get_db),
                  limit: int = Query(10, ge=1, le=100, description="Number of records per page"),
                  offset: int = Query(0, ge=0, description="Number of records to skip")):
    return ExpenseController.list_expenses(user, db, limit, offset)


@router.get("/expense/{expense_id}")
def get_expense(expense_id: int, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return ExpenseController.get_expense(expense_id, user, db)


@router.put("/expense/{expense_id}")
def update_expense(expense_id: int, payload: ExpenseUpdate, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return ExpenseController.update_expense(expense_id, payload, user, db)


@router.delete("/expense/{expense_id}")
def delete_expense(expense_id: int, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return ExpenseController.delete_expense(expense_id, user, db)

# -------- S3 ROUTES ---------------
@router.get("/attachment/view")
def view_pdf(s3_url: str, user=Depends(jwt_middleware), db: Session = Depends(get_db)):
    return FileController.get_attachment_signed_url(s3_url=s3_url, db=db)

@router.post("/upload")
async def upload_pdf_route(
    file: UploadFile = File(...),
    document_type: str = "INVOICE",
    upload_notes: str = None,
    user=Depends(jwt_middleware),
    db: Session = Depends(get_db)
):
    """Upload a PDF file and create entries in ManualUpload and Attachment tables."""
    return await FileController.upload_file(file, user, db, document_type, upload_notes)