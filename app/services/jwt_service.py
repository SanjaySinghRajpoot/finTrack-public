import jwt
import os
import datetime


JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "1440"))

class JwtService:
    def __init__(self, secret: str = JWT_SECRET, algorithm: str = JWT_ALGORITHM, expiry_minutes: int = JWT_EXPIRY_MINUTES):
        self.secret = secret
        self.algorithm = algorithm
        self.expiry_minutes = expiry_minutes

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

