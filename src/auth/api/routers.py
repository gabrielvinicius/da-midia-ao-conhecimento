# src/auth/api/routers.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from .dependencies import (
    get_auth_service,
    get_auth_queries,
    get_current_user,
    get_current_admin_user,
)
from .schemas import Token, UserResponse, UserCreate, TokenRequest, ChangePasswordRequest # Import new schema
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
    token = await auth_service.authenticate_user_and_get_token(login_data.username, login_data.password)
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
    return current_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT, summary="Change current user's password")
async def change_current_user_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Allows the currently authenticated user to change their own password."""
    try:
        await auth_service.change_password(
            user_id=current_user.id,
            old_password=password_data.old_password,
            new_password=password_data.new_password
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return


@router.get(
    "/users", 
    response_model=List[UserResponse], 
    summary="List all users (Admin only)",
    dependencies=[Depends(get_current_admin_user)]
)
async def list_all_users(
    auth_queries: AuthQueries = Depends(get_auth_queries),
):
    users = await auth_queries.list_all()
    return users
