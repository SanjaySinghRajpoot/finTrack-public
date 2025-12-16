import jwt
import datetime

from app.core.config import settings


class JwtService:
    def __init__(
        self, 
        secret: str = None, 
        algorithm: str = None, 
        expiry_minutes: int = None
    ):
        self.secret = secret or settings.JWT_SECRET
        self.algorithm = algorithm or settings.JWT_ALGORITHM
        self.expiry_minutes = expiry_minutes or settings.JWT_EXPIRY_MINUTES

    def create_token(self, user_id: int, email: str):
        payload = {
            "user_id": str(user_id),
            "email": email,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=self.expiry_minutes),
            "iat": datetime.datetime.utcnow()
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str):
        try:
            decoded = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return decoded
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

