# src/auth/utils/token.py
from datetime import datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt

from src.user_management.config.settings import AuthSettings  # Importação corrigida

settings = AuthSettings()


def create_access_token(user_id: UUID) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "exp": expire
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
