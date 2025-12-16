from starlette.responses import RedirectResponse
from urllib.parse import urlparse

from app.core.config import settings
from app.services.token_service import TokenService
from app.utils.oauth_utils import generate_auth_url
from app.utils.exceptions import ExternalServiceError


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

            response = RedirectResponse(url=settings.FRONTEND_URL or "http://localhost")

            # Determine if we're in production (HTTPS) or local (HTTP)
            is_production = settings.FRONTEND_URL and settings.FRONTEND_URL.startswith("https://")
            
            # Extract domain from FRONTEND_URL
            domain = None
            if settings.FRONTEND_URL:
                parsed_url = urlparse(settings.FRONTEND_URL)
                domain = parsed_url.hostname

            # Set cookies securely
            response.set_cookie(
                key="expense_tracker_jwt",
                value=tokens.get("jwt"),
                domain=domain if domain else None,
                httponly=False,
                secure=is_production,
                samesite="Lax",
                max_age=tokens.get("expires_in")
            )

            return response
        except Exception as e:
            raise ExternalServiceError("OAuth", f"Authentication failed: {str(e)}")
