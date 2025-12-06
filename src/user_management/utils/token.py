# src/auth/utils/token.py
from datetime import datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt

from src.shared.infrastructure.settings import settings


def create_access_token(user_id: UUID) -> str:
    # Use utcnow from shared utils if available, or datetime.utcnow()
    # Using datetime.utcnow() for now to match existing logic pattern but cleanly
    # Ideally we should use the shared time_utils
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None