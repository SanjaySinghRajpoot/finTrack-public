import os
import base64

from dotenv import load_dotenv
from fastapi import File, UploadFile
from starlette.responses import JSONResponse, RedirectResponse

from app.constants.integration_constants import FeatureKey
from app.models.models import Expense, User
from app.services.s3_service import S3Service
from app.services.token_service import TokenService
from app.services.db_service import DBService
from app.services.user_service import UserService
from app.utils.oauth_utils import generate_auth_url, exchange_code_for_tokens
from app.services.gmail_service import GmailClient
from app.models.scheme import ExpenseCreate, ExpenseUpdate
from app.utils.exceptions import (
    AuthenticationError,
    NotFoundError,
    BusinessLogicError,
    ExternalServiceError,
    DatabaseError
)
from app.services.file_service import FileProcessor
from app.models.scheme import UploadSuccessResponse, UploadSuccessData, UploadErrorResponse
from app.services.llm_service import LLMService, DocumentProcessingRequest
from app.utils.decorators import deduct_credits

load_dotenv()

VITE_API_BASE_URL = os.getenv("VITE_API_BASE_URL")


class AuthController:
    @staticmethod
    def login():
        url = generate_auth_url()
        return {"auth_url": url}

    @staticmethod
    def oauth2callback(request, code, db):
        try:
            tokens = exchange_code_for_tokens(code, db)

            token_service = TokenService(db)
            token_service.save_gmail_token(
                tokens.get("user").get("id"),
                tokens.get("user").get("email"),
                tokens.get("google_access_token"),
                tokens.get("google_refresh_token"),
                tokens.get("expires_in")
            )

            response = RedirectResponse(url= VITE_API_BASE_URL or "http://localhost:8080/")

            # Set cookies securely
            response.set_cookie(
                key="expense_tracker_jwt",
                value=tokens.get("jwt"),
                httponly=False,
                secure=True,
                samesite="Lax",
                max_age=tokens.get("expires_in")
            )

            return response
        except Exception as e:
            raise ExternalServiceError("OAuth", f"Authentication failed: {str(e)}")


class EmailController:
    @staticmethod
    async def get_emails(payload, user, db):
        user_id = user.get("user_id")

        access_token = payload.access_token
        if not access_token:
            raise AuthenticationError("Not authenticated. Please login first.")

        db_service = DBService(db)
        gmail_client = GmailClient(access_token, db_service, user_id)

        return await gmail_client.fetch_emails()


class ProcessedDataController:
    @staticmethod
    def get_payment_info(user, db, limit: int, offset: int):
        user_id = user.get("user_id")
        db_service = DBService(db)
        return db_service.get_processed_data(user_id=user_id, limit=limit, offset=offset)


class ExpenseController:
    @staticmethod
    def create_expense(payload: ExpenseCreate, user, db):
        try:
            db_service = DBService(db)
            expense = Expense(
                user_id=user.get("user_id"),
                amount=payload.amount,
                currency=payload.currency,
                category=payload.category,
                description=payload.description
            )

            if payload.is_import:
                # Get the processed data to extract source_id
                processed_data = db_service.get_processed_data_by_id(payload.processed_data_id)
                if processed_data:
                    expense.source_id = processed_data.source_id
                
                db_service.import_processed_data(payload.processed_data_id)

            return db_service.create_expense(expense)
        except Exception as e:
            raise DatabaseError(f"Failed to create expense: {str(e)}")

    @staticmethod
    def list_expenses(user, db, limit: int, offset: int):
        try:
            db_service = DBService(db)
            return db_service.list_expenses(user.get("user_id"), limit, offset)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve expenses: {str(e)}")

    @staticmethod
    def get_expense(expense_id: int, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_id, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_id))
            return expense
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve expense: {str(e)}")

    @staticmethod
    def update_expense(expense_id: int, payload: ExpenseUpdate, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_id, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_id))

            return db_service.update_expense(expense, payload.to_dict())
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update expense: {str(e)}")

    @staticmethod
    def delete_expense(expense_id: int, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_id, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_id))
            return db_service.soft_delete_expense(expense)
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to delete expense: {str(e)}")

class FileController:

    @staticmethod
    def get_attachment(email_id: int, db):
        try:
            db_service = DBService(db)
            # Get attachments by email_id (which internally finds source_id)
            attachments = db_service.get_attachments_by_email_id(email_id)
            return attachments[0] if attachments else None
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve attachment: {str(e)}")
        
    @staticmethod
    @deduct_credits(feature_key=FeatureKey.FILE_UPLOAD.value)
    async def upload_file(**kwargs):
        """
        Upload a PDF file or image manually for a user with complete validation and error handling.
        
        Args:
            file: The uploaded file
            user: Authenticated user object from JWT middleware
            db: Database session
            document_type: Type of document (default: INVOICE)
            upload_notes: Optional notes about the upload
            
        Returns:
            JSONResponse with structured Pydantic response models
        """
        # Extract parameters from kwargs
        file = kwargs.get('file')
        user = kwargs.get('user')
        db = kwargs.get('db')
        document_type = kwargs.get('document_type', 'INVOICE')
        upload_notes = kwargs.get('upload_notes')
        
        try:
            # Validate file type - support both PDFs and images
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.webp'}
            file_extension = file.filename.lower()
            
            if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                error_response = UploadErrorResponse(error="Only PDF and image files (JPG, PNG, WEBP) are supported")
                return JSONResponse(
                    status_code=400, 
                    content=error_response.dict()
                )
            
            # Determine if file is PDF or image
            is_pdf = file_extension.endswith('.pdf')
            is_image = file_extension.endswith(('.jpg', '.jpeg', '.png', '.webp'))
            
            # Validate file size (e.g., max 10MB)
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
            file_content = await file.read()
            if len(file_content) > MAX_FILE_SIZE:
                error_response = UploadErrorResponse(error="File size exceeds 10MB limit")
                return JSONResponse(
                    status_code=400,
                    content=error_response.dict()
                )
            
            # Reset file position for processing
            await file.seek(0)
            
            # Generate file hash for duplicate detection
            from app.services.file_service import FileHashUtils
            file_hash = await FileHashUtils.generate_file_hash(file)
            
            # Check for duplicate files
            db_service = DBService(db)
            duplicate_check = db_service.check_duplicate_file_by_hash(file_hash, user.get("user_id"))
            
            if duplicate_check.is_duplicate:
                error_response = UploadErrorResponse(
                    error=f"Duplicate file detected. This file was already uploaded as '{duplicate_check.existing_filename}'"
                )
                return JSONResponse(
                    status_code=409,  # Conflict status code for duplicates
                    content=error_response.dict()
                )
            
            # Reset file position again after hash generation
            await file.seek(0)
            
            # Initialize file processor
            file_processor = FileProcessor(db_service, user.get("user_id"))
            
            # Step 1: Upload file and generate hash (FileProcessor handles this)
            upload_result = await file_processor.upload_file_with_hash(
                file=file,
                file_hash=file_hash
            )
            
            # Step 2: For PDFs - extract text; For images - convert to base64
            text_content = None
            image_base64 = None
            
            if is_pdf:
                # Extract text from PDF
                text_content = file_processor.extract_text(upload_result["file_data"])
            elif is_image:
                # Convert image to base64
                image_base64 = base64.b64encode(upload_result["file_data"]).decode("utf-8")
            
            # Step 3: Create manual upload entry (triggers Source creation)
            manual_upload = file_processor._create_manual_upload_entry(
                user_id=user.get("user_id"),
                document_type=document_type.upper(),
                upload_notes=upload_notes
            )
            
            # Step 4: Get the source created by event handler
            source = file_processor._get_source_from_manual_upload(manual_upload.id)
            
            # Step 5: Create attachment entry
            attachment = file_processor._create_attachment_entry(
                source_id=source.id,
                user_id=user.get("user_id"),
                filename=upload_result["filename"],
                file_data=upload_result["file_data"],
                s3_key=upload_result["s3_key"],
                file_hash=upload_result["file_hash"],
                mime_type=upload_result["mime_type"],
                extracted_text=text_content
            )
            
            # Step 6: Commit transaction
            db_service.commit()
            
            # Step 7: Process with LLM based on file type
            try:
                llm_service = LLMService(user.get("user_id"), db_service)
                
                if is_pdf and text_content:
                    # PDF: Use text-based processing
                    processing_request = DocumentProcessingRequest(
                        source_id=source.id,
                        user_id=user.get("user_id"),
                        document_type="manual_upload",
                        text_content=text_content,
                        metadata={
                            "filename": upload_result["filename"],
                            "s3_key": upload_result["s3_key"],
                            "upload_method": "web_upload",
                            "upload_notes": upload_notes,
                            "file_hash": upload_result["file_hash"]
                        }
                    )
                    llm_results = llm_service.llm_manual_processing([processing_request])
                    print(f"LLM PDF processing completed with {len(llm_results)} results")
                    
                elif is_image and image_base64:
                    # Image: Use vision-based processing with base64
                    processing_request = DocumentProcessingRequest(
                        source_id=source.id,
                        user_id=user.get("user_id"),
                        document_type="manual_upload",
                        image_base64=image_base64,  # Pass base64 directly
                        metadata={
                            "filename": upload_result["filename"],
                            "s3_key": upload_result["s3_key"],
                            "upload_method": "web_upload",
                            "upload_notes": upload_notes,
                            "file_hash": upload_result["file_hash"],
                            "mime_type": upload_result["mime_type"]
                        }
                    )
                    llm_results = llm_service.llm_image_processing_batch([processing_request])
                    print(f"LLM image processing completed with {len(llm_results)} results")
                    
            except Exception as llm_error:
                print(f"LLM processing failed: {llm_error}")
                # Don't fail the upload if LLM processing fails
            
            # Create structured success response
            success_data = UploadSuccessData(
                success=True,
                attachment_id=attachment.id,
                manual_upload_id=manual_upload.id,
                filename=upload_result["filename"],
                s3_key=upload_result["s3_key"],
                file_size=upload_result["file_size"],
                document_type=document_type
            )
            
            success_response = UploadSuccessResponse(
                message="File uploaded successfully",
                data=success_data
            )
            
            return JSONResponse(
                status_code=200,
                content=success_response.dict()
            )
            
        except Exception as e:
            # Rollback on any error
            db_service.db.rollback()
            error_response = UploadErrorResponse(error=f"Upload failed: {str(e)}")
            return JSONResponse(
                status_code=500, 
                content=error_response.dict()
            )

    @staticmethod
    def get_attachment_signed_url(s3_url: str, db):
        try:
            s3 = S3Service()
            signed_url = s3.get_presigned_url(s3_url)

            return {
                "url": signed_url
            } 

        except NotFoundError:
            raise
        except Exception as e:
            raise ExternalServiceError("S3", f"Failed to generate signed URL: {str(e)}")


class UserController:

    @staticmethod
    async def get_user_info(user: dict, db):
        try:
            db_service = DBService(db)
            user_obj = db_service.get_user_by_id(user.get("user_id"))
            
            if not user_obj:
                raise NotFoundError("User", str(user.get("user_id")))

            return user_obj
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user info: {str(e)}")

    @staticmethod
    async def update_user_details(user: dict, update_details: dict, db):
        try:
            db_service = DBService(db)
            db_service.update_user_details(user.get("user_id"), update_details)
        except Exception as e:
            raise DatabaseError(f"Failed to update user details: {str(e)}")

    @staticmethod
    async def get_user_settings(user: dict, db):
        try:
            user_service = UserService()
            return await user_service.get_user_settings(user, db)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user settings: {str(e)}")








