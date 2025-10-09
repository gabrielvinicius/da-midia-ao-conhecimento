# src/shared/middleware/validation_middleware.py
"""
Middleware para validação automática de requests e responses.
Integra com o sistema de exceções de domínio.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError
from typing import Callable
import json

from src.shared.validation.schemas import create_validation_error_response
from src.shared.infrastructure.logging_config import get_logger
from src.shared.exceptions.domain_exceptions import ValidationError as DomainValidationError

logger = get_logger("validation_middleware")


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware para interceptar e tratar erros de validação."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            # Log da requisição para debugging
            logger.debug("Request received", 
                        method=request.method,
                        path=request.url.path,
                        query_params=str(request.query_params))
            
            response = await call_next(request)
            
            # Log da resposta para debugging
            logger.debug("Response sent",
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code)
            
            return response
            
        except ValidationError as e:
            # Interceptar erros de validação do Pydantic
            logger.warning("Pydantic validation error occurred",
                          path=request.url.path,
                          method=request.method,
                          errors=e.errors())
            
            error_response = create_validation_error_response(e.errors())
            
            return JSONResponse(
                status_code=422,
                content=error_response.dict()
            )
            
        except DomainValidationError as e:
            # Interceptar erros de validação de domínio
            logger.warning("Domain validation error occurred",
                          path=request.url.path,
                          method=request.method,
                          error_code=e.error_code,
                          message=e.message)
            
            return JSONResponse(
                status_code=400,
                content=e.to_dict()
            )
            
        except Exception as e:
            # Log outros erros para investigação
            logger.error("Unexpected error in validation middleware",
                        path=request.url.path,
                        method=request.method,
                        error_type=type(e).__name__,
                        error_message=str(e))
            raise


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware para validar tamanho de requisições."""
    
    def __init__(self, app, max_request_size: int = 100 * 1024 * 1024):  # 100MB default
        super().__init__(app)
        self.max_request_size = max_request_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Verificar Content-Length header
        content_length = request.headers.get('content-length')
        
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_request_size:
                logger.warning("Request too large",
                              path=request.url.path,
                              content_length=content_length,
                              max_allowed=self.max_request_size)
                
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "REQUEST_TOO_LARGE",
                        "message": f"Request size {content_length} exceeds maximum allowed size {self.max_request_size}",
                        "details": {
                            "max_size_bytes": self.max_request_size,
                            "received_size_bytes": content_length
                        }
                    }
                )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para adicionar headers de segurança."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Adicionar headers de segurança
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


def register_validation_middleware(app):
    """Registra todos os middlewares de validação."""
    
    # Ordem importa - middlewares são executados em ordem reversa
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeMiddleware, max_request_size=100 * 1024 * 1024)  # 100MB
    app.add_middleware(ValidationMiddleware)
    
    logger.info("Validation middlewares registered successfully")