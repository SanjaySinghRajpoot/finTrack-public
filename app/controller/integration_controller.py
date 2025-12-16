from app.core.config import settings
from app.utils.exceptions import (
    AuthenticationError,
    NotFoundError,
    BusinessLogicError,
    DatabaseError
)


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
                redirect_url = f"{settings.FRONTEND_URL}/settings?integration=gmail&status=success"
                return RedirectResponse(url=redirect_url)
            else:
                raise NotFoundError("Integration", slug,
                                  details={"message": f"Integration '{slug}' not supported"})
                
        except (NotFoundError, AuthenticationError, DatabaseError) as e:
            # Redirect to frontend with error
            error_msg = str(e)
            redirect_url = f"{settings.FRONTEND_URL}/settings?integration={slug}&status=error&message={error_msg}"
            return RedirectResponse(url=redirect_url)
        except Exception as e:
            # Redirect to frontend with generic error
            redirect_url = f"{settings.FRONTEND_URL}/settings?integration={slug}&status=error&message=Failed to complete integration"
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
