from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.jwt_service import JwtService

security = HTTPBearer(auto_error=True)

def jwt_middleware(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_service: JwtService = Depends(lambda: JwtService())
):
    token = credentials.credentials
    try:
        payload = jwt_service.verify_token(token)
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
