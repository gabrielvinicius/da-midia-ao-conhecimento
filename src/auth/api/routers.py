# src/auth/api/routers.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .dependencies import (
    get_auth_service,
    get_auth_queries,
    get_current_user,
    get_current_admin_user,
)
from .schemas import Token, UserResponse, UserCreate, TokenRequest
from src.auth.application.auth_service import AuthService
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.domain.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED, 
    summary="Register a new user",
    responses={400: {"description": "Email already registered"}}
)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Registers a new user with a unique email and password."""
    try:
        user = await auth_service.create_user(user_data.email, user_data.password)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/token", 
    response_model=Token, 
    summary="Log in to get an access token",
    responses={401: {"description": "Invalid credentials"}}
)
async def login_json(
    login_data: TokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logs a user in using JSON credentials to get a JWT access token."""
    token = await auth_service.authenticate_user_and_get_token(login_data.username, login_data.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/token/form", response_model=Token, include_in_schema=False)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logs a user in using form data (for OAuth2 compatible clients)."""
    token = await auth_service.authenticate_user_and_get_token(form_data.username, form_data.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return {"access_token": token, "token_type": "bearer"}


@router.get(
    "/me", 
    response_model=UserResponse, 
    summary="Get current user details",
    responses={401: {"description": "Could not validate credentials"}}
)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """Retrieves the currently authenticated user's details."""
    return current_user


@router.get(
    "/users", 
    response_model=List[UserResponse], 
    summary="List all users (Admin only)",
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Not enough privileges"}}
)
async def list_all_users(
    auth_queries: AuthQueries = Depends(get_auth_queries),
    _: User = Depends(get_current_admin_user),
):
    """Lists all users in the system. Requires admin privileges."""
    users = await auth_queries.list_all()
    return users
