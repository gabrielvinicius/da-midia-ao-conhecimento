# auth adapter for FastAPI OAuth2 password flow
from fastapi.security import OAuth2PasswordBearer

# Simple OAuth2 scheme without circular dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
