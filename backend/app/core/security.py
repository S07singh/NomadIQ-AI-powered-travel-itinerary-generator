"""Password hashing and JWT helpers (stateless access tokens + rotating refresh tokens)."""

import uuid
from datetime import datetime, timedelta

import bcrypt
import jwt

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.core.utils import utcnow

ACCESS = "access"
REFRESH = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(settings: Settings, user_id: str, token_type: str) -> tuple[str, str, datetime]:
    """Return (encoded_token, jti, expires_at)."""
    now = utcnow()
    if token_type == ACCESS:
        expires = now + timedelta(minutes=settings.access_token_ttl_minutes)
    else:
        expires = now + timedelta(days=settings.refresh_token_ttl_days)
    jti = uuid.uuid4().hex
    payload = {"sub": user_id, "type": token_type, "jti": jti, "iat": now, "exp": expires}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti, expires


def decode_token(settings: Settings, token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token expired", code="token_expired")
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid token", code="invalid_token")
    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type", code="invalid_token")
    return payload
