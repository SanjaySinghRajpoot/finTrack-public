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
        print(f"[JWT] Creating token with secret: {self.secret[:10]}... algorithm: {self.algorithm}")
        payload = {
            "user_id": str(user_id),
            "email": email,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=self.expiry_minutes),
            "iat": datetime.datetime.utcnow()
        }
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        print(f"[JWT] Token created successfully for user_id: {user_id}")
        return token

    def verify_token(self, token: str):
        print(f"[JWT] Verifying token with secret: {self.secret[:10]}... algorithm: {self.algorithm}")
        try:
            decoded = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            print(f"[JWT] Token verified successfully for user_id: {decoded.get('user_id')}")
            return decoded
        except jwt.ExpiredSignatureError:
            print("[JWT] Token verification failed: Token has expired")
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            print(f"[JWT] Token verification failed: Invalid token - {str(e)}")
            raise ValueError("Invalid token")

