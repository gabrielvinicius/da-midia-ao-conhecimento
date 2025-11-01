# src/auth/infrastructure/secure_auth.py
"""
Sistema de autenticação segura com cookies httpOnly e proteção CSRF.
Remove dependência do localStorage para maior segurança.
"""

from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import secrets
import hashlib
from jose import jwt, JWTError

from src.user_management.config.settings import AuthSettings
from src.user_management.domain.user import User
from src.shared.infrastructure.logging_config import get_logger
from src.shared.exceptions.domain_exceptions import AuthenticationError, AuthorizationError

logger = get_logger("secure_auth")
settings = AuthSettings()

# Storage seguro para tokens CSRF
csrf_tokens: Dict[str, Dict[str, Any]] = {}

class SecureTokenManager:
    """Gerenciador seguro de tokens com cookies httpOnly."""
    
    COOKIE_NAME = "auth_token"
    CSRF_COOKIE_NAME = "csrf_token"
    REFRESH_COOKIE_NAME = "refresh_token"
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = 7  # Refresh token válido por 7 dias
    
    def create_access_token(self, user_id: str, additional_claims: Dict[str, Any] = None) -> str:
        """Cria um access token JWT."""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Cria um refresh token JWT."""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verifica e decodifica um token JWT."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verificar se é o tipo correto de token
            if payload.get("type") != token_type:
                logger.warning("Token type mismatch", 
                             expected=token_type, 
                             actual=payload.get("type"))
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning("Token verification failed", error=str(e))
            return None
    
    def generate_csrf_token(self, user_id: str) -> str:
        """Gera um token CSRF único."""
        token = secrets.token_urlsafe(32)
        
        # Armazenar token com timestamp para expiração
        csrf_tokens[user_id] = {
            "token": token,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24)
        }
        
        logger.debug("CSRF token generated", user_id=user_id)
        return token
    
    def verify_csrf_token(self, user_id: str, provided_token: str) -> bool:
        """Verifica se o token CSRF é válido."""
        stored_data = csrf_tokens.get(user_id)
        
        if not stored_data:
            logger.warning("No CSRF token found for user", user_id=user_id)
            return False
        
        # Verificar expiração
        if datetime.utcnow() > stored_data["expires_at"]:
            logger.warning("CSRF token expired", user_id=user_id)
            del csrf_tokens[user_id]
            return False
        
        # Verificar token usando comparação segura
        is_valid = secrets.compare_digest(stored_data["token"], provided_token)
        
        if not is_valid:
            logger.warning("CSRF token mismatch", user_id=user_id)
        
        return is_valid
    
    def set_auth_cookies(self, response: Response, user_id: str) -> Dict[str, str]:
        """Define cookies de autenticação seguros."""
        # Criar tokens
        access_token = self.create_access_token(user_id)
        refresh_token = self.create_refresh_token(user_id)
        csrf_token = self.generate_csrf_token(user_id)
        
        # Configurar cookies httpOnly
        response.set_cookie(
            key=self.COOKIE_NAME,
            value=access_token,
            max_age=self.access_token_expire_minutes * 60,
            httponly=True,
            secure=True,  # HTTPS only em produção
            samesite="lax"
        )
        
        response.set_cookie(
            key=self.REFRESH_COOKIE_NAME,
            value=refresh_token,
            max_age=self.refresh_token_expire_days * 24 * 60 * 60,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        # CSRF token deve ser acessível ao JavaScript para incluir em headers
        response.set_cookie(
            key=self.CSRF_COOKIE_NAME,
            value=csrf_token,
            max_age=24 * 60 * 60,  # 24 horas
            httponly=False,  # Deve ser acessível ao JavaScript
            secure=True,
            samesite="lax"
        )
        
        logger.info("Auth cookies set successfully", user_id=user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "csrf_token": csrf_token
        }
    
    def clear_auth_cookies(self, response: Response):
        """Remove todos os cookies de autenticação."""
        cookies_to_clear = [
            self.COOKIE_NAME,
            self.REFRESH_COOKIE_NAME,
            self.CSRF_COOKIE_NAME
        ]
        
        for cookie_name in cookies_to_clear:
            response.delete_cookie(
                key=cookie_name,
                httponly=True,
                secure=True,
                samesite="lax"
            )
        
        logger.info("Auth cookies cleared")
    
    def get_token_from_cookie(self, request: Request) -> Optional[str]:
        """Extrai o token de acesso do cookie."""
        return request.cookies.get(self.COOKIE_NAME)
    
    def get_csrf_token_from_cookie(self, request: Request) -> Optional[str]:
        """Extrai o token CSRF do cookie."""
        return request.cookies.get(self.CSRF_COOKIE_NAME)


class SecureHTTPBearer(HTTPBearer):
    """HTTPBearer customizado que suporta cookies e tokens de header."""
    
    def __init__(self, token_manager: SecureTokenManager):
        super().__init__(auto_error=False)
        self.token_manager = token_manager
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        # Primeiro tentar obter do header Authorization
        credentials = await super().__call__(request)
        
        if credentials:
            return credentials
        
        # Se não encontrou no header, tentar no cookie
        token = self.token_manager.get_token_from_cookie(request)
        if token:
            return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        return None


# Instâncias globais
token_manager = SecureTokenManager()
secure_bearer = SecureHTTPBearer(token_manager)


async def get_current_user_secure(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None
) -> User:
    """
    Extrai e valida o usuário atual usando autenticação segura.
    Suporta tanto tokens em headers quanto em cookies.
    """
    if not credentials:
        credentials = await secure_bearer(request)
    
    if not credentials:
        logger.warning("No authentication credentials provided", 
                      path=request.url.path,
                      method=request.method)
        raise AuthenticationError("Authentication credentials required")
    
    # Verificar token
    payload = token_manager.verify_token(credentials.credentials, "access")
    if not payload:
        logger.warning("Invalid or expired token", 
                      path=request.url.path,
                      method=request.method)
        raise AuthenticationError("Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")
    
    # Aqui você injetaria o AuthService para buscar o usuário
    # Por agora, retornamos o user_id
    logger.debug("User authenticated successfully", user_id=user_id)
    return user_id  # Em implementação real, retornaria User object


async def verify_csrf_protection(request: Request, user_id: str) -> bool:
    """
    Verifica proteção CSRF para requisições que modificam dados.
    """
    # CSRF é necessário apenas para métodos que modificam estado
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return True
    
    # Obter token CSRF do header
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_header:
        logger.warning("Missing CSRF token in header", 
                      user_id=user_id,
                      method=request.method,
                      path=request.url.path)
        raise AuthorizationError("CSRF token required", "CSRF protection")
    
    # Verificar token CSRF
    if not token_manager.verify_csrf_token(user_id, csrf_header):
        logger.warning("Invalid CSRF token", 
                      user_id=user_id,
                      method=request.method,
                      path=request.url.path)
        raise AuthorizationError("Invalid CSRF token", "CSRF protection")
    
    logger.debug("CSRF verification successful", user_id=user_id)
    return True


# Função para limpeza periódica de tokens CSRF expirados
async def cleanup_expired_csrf_tokens():
    """Remove tokens CSRF expirados do storage."""
    current_time = datetime.utcnow()
    expired_users = [
        user_id for user_id, data in csrf_tokens.items()
        if current_time > data["expires_at"]
    ]
    
    for user_id in expired_users:
        del csrf_tokens[user_id]
    
    if expired_users:
        logger.info("Cleaned up expired CSRF tokens", count=len(expired_users))
