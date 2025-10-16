# src/auth/api/routers.py
from typing import List, Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from jose import JWTError, jwt

from .schemas import Token, UserResponse, UserCreate, TokenRequest, ChangePasswordRequest
from src.auth.application.auth_service import AuthService
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.domain.user import User, UserRole
from src.auth.config.settings import AuthSettings
from src.auth.infrastructure.oauth2_scheme import oauth2_scheme

# --- Dependency Injection and Security Logic (Now Local to this Router) ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_auth_service(container: Annotated[dict, Depends(get_container)]) -> AuthService:
    return container["auth_service"]

def get_auth_queries(container: Annotated[dict, Depends(get_container)]) -> AuthQueries:
    return container["auth_queries"]

def get_auth_settings(container: Annotated[dict, Depends(get_container)]) -> AuthSettings:
    return container["auth_settings"]

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    queries: Annotated[AuthQueries, Depends(get_auth_queries)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await queries.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The user does not have enough privileges")
    return current_user

# --- Router Definition ---

router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- Endpoints ---

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.create_user(user_data.email, user_data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
):
    token = await auth_service.authenticate_user_and_get_token(form_data.username, form_data.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user

@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(get_current_admin_user)])
async def list_all_users(auth_queries: AuthQueries = Depends(get_auth_queries)):
    return await auth_queries.list_all()
