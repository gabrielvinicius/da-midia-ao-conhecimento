# auth/infrastructure/oauth2_scheme.py
from fastapi.security import OAuth2PasswordBearer

# Simple OAuth2 scheme without circular dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
