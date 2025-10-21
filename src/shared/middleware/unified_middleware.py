"""
Unified middleware - eliminating middleware duplication
"""
import time
import structlog
from typing import Callable, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import JSONResponse

from src.shared.infrastructure.unified_metrics import unified_metrics

logger = structlog.get_logger(__name__)

class UnifiedMiddleware(BaseHTTPMiddleware):
    """Single middleware combining all cross-cutting concerns"""
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        
        # Configuration with defaults
        self.max_request_size = self.config.get('max_request_size', 100 * 1024 * 1024)  # 100MB
        self.rate_limit = self.config.get('rate_limit', 100)
        self.rate_window = self.config.get('rate_window', 60)
        self.enable_metrics = self.config.get('enable_metrics', True)
        self.enable_logging = self.config.get('enable_logging', True)
        
        # Rate limiting storage (in memory - use Redis in production)
        self._rate_limit_storage: Dict[str, Dict] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Unified request processing"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        try:
            # 1. Request size validation
            if not await self._validate_request_size(request):
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request too large"}
                )
            
            # 2. Rate limiting
            if not self._check_rate_limit(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded"}
                )
            
            # 3. Log request
            if self.enable_logging:
                logger.info("Request started",
                          method=request.method,
                          path=request.url.path,
                          client_ip=client_ip)
            
            # 4. Process request
            response = await call_next(request)
            
            # 5. Add performance headers
            duration = time.time() - start_time
            response.headers["X-Process-Time"] = str(duration)
            response.headers["X-Server"] = "unified-api"
            
            # 6. Record metrics
            if self.enable_metrics:
                unified_metrics.record_histogram(
                    name="http_request_duration_seconds",
                    value=duration,
                    labels={
                        "method": request.method,
                        "path": request.url.path,
                        "status": str(response.status_code)
                    }
                )
                
                unified_metrics.record_counter(
                    name="http_requests_total",
                    labels={
                        "method": request.method,
                        "path": request.url.path,
                        "status": str(response.status_code)
                    }
                )
            
            # 7. Log response
            if self.enable_logging:
                logger.info("Request completed",
                          method=request.method,
                          path=request.url.path,
                          status=response.status_code,
                          duration=duration)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            logger.error("Request failed",
                        method=request.method,
                        path=request.url.path,
                        error=str(e),
                        duration=duration)
            
            # Record error metrics
            if self.enable_metrics:
                unified_metrics.record_counter(
                    name="http_errors_total",
                    labels={
                        "method": request.method,
                        "path": request.url.path,
                        "error_type": type(e).__name__
                    }
                )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(e) if self.config.get('debug', False) else "An error occurred"
                }
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    async def _validate_request_size(self, request: Request) -> bool:
        """Validate request size"""
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                size = int(content_length)
                return size <= self.max_request_size
            except ValueError:
                return True  # Allow if we can't parse
        return True
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Simple rate limiting"""
        if not self.rate_limit:
            return True
        
        now = time.time()
        window_start = now - self.rate_window
        
        # Clean old entries
        if client_ip in self._rate_limit_storage:
            requests = self._rate_limit_storage[client_ip].get('requests', [])
            recent_requests = [req_time for req_time in requests if req_time > window_start]
            self._rate_limit_storage[client_ip]['requests'] = recent_requests
        else:
            self._rate_limit_storage[client_ip] = {'requests': []}
        
        # Check limit
        current_requests = len(self._rate_limit_storage[client_ip]['requests'])
        if current_requests >= self.rate_limit:
            return False
        
        # Add current request
        self._rate_limit_storage[client_ip]['requests'].append(now)
        return True

# CORS middleware for API
class SimpleCORSMiddleware(BaseHTTPMiddleware):
    """Simple CORS middleware"""
    
    def __init__(self, app, allowed_origins: list = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        # Add CORS headers
        origin = request.headers.get("origin")
        if origin and (origin in self.allowed_origins or "*" in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "86400"
        
        return response

# Factory function for easy setup
def create_unified_middleware(config: Dict[str, Any] = None) -> UnifiedMiddleware:
    """Create unified middleware with configuration"""
    return UnifiedMiddleware(None, config)

def setup_middleware(app, config: Dict[str, Any] = None):
    """Setup all middleware for FastAPI app"""
    
    # Add unified middleware
    app.add_middleware(
        UnifiedMiddleware,
        config=config or {}
    )
    
    # Add CORS if needed
    cors_origins = config.get('cors_origins', ["*"]) if config else ["*"]
    app.add_middleware(SimpleCORSMiddleware, allowed_origins=cors_origins)
    
    logger.info("Unified middleware setup completed")