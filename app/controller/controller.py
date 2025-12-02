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
from app.utils.oauth_utils import generate_auth_url
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
FRONTEND_URL = os.getenv("FRONTEND_URL")


class AuthController:
    @staticmethod
    async def login():
        url = generate_auth_url()
        return {"auth_url": url}

    @staticmethod
    async def oauth2callback(request, code, db):
        try:
            token_service = TokenService(db)
            tokens = await token_service.exchange_code_for_tokens(code)

            response = RedirectResponse(url=FRONTEND_URL or "http://localhost")

            # Determine if we're in production (HTTPS) or local (HTTP)
            is_production = FRONTEND_URL and FRONTEND_URL.startswith("https://")
            
            # Extract domain from FRONTEND_URL
            domain = None
            if FRONTEND_URL:
                # Extract domain from URL (e.g., "https://15.206.194.238.nip.io" -> "15.206.194.238.nip.io")
                from urllib.parse import urlparse
                parsed_url = urlparse(FRONTEND_URL)
                domain = parsed_url.hostname

            # Set cookies securely
            response.set_cookie(
                key="expense_tracker_jwt",
                value=tokens.get("jwt"),
                domain=domain if domain else None,  # Use extracted domain or None for localhost
                httponly=False,
                secure=is_production,  # True for HTTPS, False for HTTP
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
    async def get_payment_info(user, db, limit: int, offset: int):
        user_id = user.get("user_id")
        db_service = DBService(db)
        return db_service.get_processed_data(user_id=user_id, limit=limit, offset=offset)


class ExpenseController:
    @staticmethod
    async def create_expense(payload: ExpenseCreate, user, db):
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
                if (processed_data):
                    expense.source_id = processed_data.source_id
                
                db_service.import_processed_data(payload.processed_data_id)

            return db_service.create_expense(expense)
        except Exception as e:
            raise DatabaseError(f"Failed to create expense: {str(e)}")

    @staticmethod
    async def list_expenses(user, db, limit: int, offset: int):
        try:
            db_service = DBService(db)
            return db_service.list_expenses(user.get("user_id"), limit, offset)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve expenses: {str(e)}")

    @staticmethod
    async def get_expense(expense_uuid: str, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_uuid, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_uuid))
            return expense
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve expense: {str(e)}")

    @staticmethod
    async def update_expense(expense_uuid: str, payload: ExpenseUpdate, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_uuid, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_uuid))

            return db_service.update_expense(expense, payload.to_dict())
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update expense: {str(e)}")

    @staticmethod
    async def delete_expense(expense_uuid: str, user, db):
        try:
            db_service = DBService(db)
            expense = db_service.get_expense(expense_uuid, user.get("user_id"))
            if not expense:
                raise NotFoundError("Expense", str(expense_uuid))
            return db_service.soft_delete_expense(expense)
        except NotFoundError:
            raise
        except DatabaseError:
            # Re-raise database errors as they already have clean messages
            raise
        except Exception as e:
            raise DatabaseError("Failed to delete expense")


class FileController:

    @staticmethod
    async def get_attachment(email_id: int, db):
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
            if (len(file_content) > MAX_FILE_SIZE):
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
    async def get_attachment_signed_url(s3_url: str, db):
        try:
            s3 = S3Service()
            signed_url = await s3.get_presigned_url(s3_url)

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
            user_service = UserService(db)
            return await user_service.get_user_settings(user, db)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user settings: {str(e)}")


class IntegrationController:
    """
    Controller for managing integrations (Gmail, WhatsApp, etc.)
    """
    
    @staticmethod
    async def link_integration(slug: str, user: dict, db):
        """
        Initiate integration linking based on slug.
        
        Args:
            slug: Integration identifier (e.g., 'gmail', 'whatsapp')
            user: Authenticated user
            db: Database session
            
        Returns:
            Integration-specific response (e.g., OAuth URL for Gmail)
        """
        try:
            # Route to appropriate integration handler based on slug
            if slug == "gmail":
                from app.services.integration.gmail_integration import GmailIntegrationService
                gmail_service = GmailIntegrationService(db)
                return await gmail_service.link_integration(user)
            else:
                raise NotFoundError("Integration", slug, 
                                  details={"message": f"Integration '{slug}' not supported"})
                
        except NotFoundError:
            raise
        except Exception as e:
            raise BusinessLogicError(f"Failed to initiate {slug} integration", 
                                   details={"error": str(e)})
    
    @staticmethod
    async def oauth_callback(slug: str, code: str, state: str, db):
        """
        Handle OAuth callback for integration (public endpoint).
        Extracts user_id from state parameter and redirects to frontend.
        
        Args:
            slug: Integration identifier (e.g., 'gmail')
            code: Authorization code from OAuth provider
            state: State parameter containing encoded user_id
            db: Database session
            
        Returns:
            Redirect to frontend with success/error status
        """
        try:
            from app.utils.oauth_utils import decode_oauth_state
            from fastapi.responses import RedirectResponse
            
            # Decode state to get user_id
            if not state:
                raise AuthenticationError("Missing state parameter in OAuth callback")
            
            state_data = decode_oauth_state(state)
            user_id = state_data.get("user_id")
            
            if not user_id:
                raise AuthenticationError("Invalid state parameter - missing user_id")
            
            # Create user dict for service methods
            user = {"user_id": user_id}
            
            # Route to appropriate integration handler based on slug
            if slug == "gmail":
                from app.services.integration.gmail_integration import GmailIntegrationService
                gmail_service = GmailIntegrationService(db)
                result = await gmail_service.oauth_callback(code, user)
                
                # Redirect to frontend settings page with success message
                redirect_url = f"{FRONTEND_URL}/settings?integration=gmail&status=success"
                return RedirectResponse(url=redirect_url)
            else:
                raise NotFoundError("Integration", slug,
                                  details={"message": f"Integration '{slug}' not supported"})
                
        except (NotFoundError, AuthenticationError, DatabaseError) as e:
            # Redirect to frontend with error
            error_msg = str(e)
            redirect_url = f"{FRONTEND_URL}/settings?integration={slug}&status=error&message={error_msg}"
            return RedirectResponse(url=redirect_url)
        except Exception as e:
            # Redirect to frontend with generic error
            redirect_url = f"{FRONTEND_URL}/settings?integration={slug}&status=error&message=Failed to complete integration"
            return RedirectResponse(url=redirect_url)
    
    @staticmethod
    async def delink_integration(slug: str, user: dict, db):
        """
        Delink/disconnect an integration.
        
        Args:
            slug: Integration identifier (e.g., 'gmail')
            user: Authenticated user
            db: Database session
            
        Returns:
            Success message
        """
        try:
            # Route to appropriate integration handler based on slug
            if slug == "gmail":
                from app.services.integration.gmail_integration import GmailIntegrationService
                gmail_service = GmailIntegrationService(db)
                return await gmail_service.delink_integration(user)
            else:
                raise NotFoundError("Integration", slug,
                                  details={"message": f"Integration '{slug}' not supported"})
                
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to delink {slug} integration",
                              details={"error": str(e)})

