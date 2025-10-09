# src/auth/api/routers.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request

from .dependencies import (
    get_auth_service,
    get_auth_queries,
    get_current_user,
    get_current_admin_user,
)
from .schemas import Token, UserResponse, UserCreate, TokenRequest, ChangePasswordRequest # Import new schema
from src.auth.infrastructure.secure_auth import token_manager, get_current_user_secure, verify_csrf_protection
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
    summary="Log in with secure cookies",
    responses={401: {"description": "Invalid credentials"}}
)
async def login_secure(
    response: Response,
    login_data: TokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Login seguro que define cookies httpOnly ao invés de retornar tokens."""
    # Autenticar usuário
    user = await auth_service.authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    # Definir cookies seguros
    tokens = token_manager.set_auth_cookies(response, str(user.id))
    
    return {
        "access_token": "set_in_cookie", 
        "token_type": "bearer",
        "csrf_token": tokens["csrf_token"]  # CSRF token para o frontend
    }


@router.post(
    "/token/legacy", 
    response_model=Token, 
    summary="Legacy login (returns token in response body)",
    responses={401: {"description": "Invalid credentials"}},
    deprecated=True
)
async def login_legacy(
    login_data: TokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Login legacy para compatibilidade - use /token para autenticação segura."""
    token = await auth_service.authenticate_user_and_get_token(login_data.username, login_data.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return {"access_token": token, "token_type": "bearer"}


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Secure logout - clears all auth cookies"
)
async def logout_secure(response: Response):
    """Logout seguro que remove todos os cookies de autenticação."""
    token_manager.clear_auth_cookies(response)
    return


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token using refresh token",
    responses={401: {"description": "Invalid refresh token"}}
)
async def refresh_token(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Renova o access token usando o refresh token."""
    refresh_token = request.cookies.get(token_manager.REFRESH_COOKIE_NAME)
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    # Verificar refresh token
    payload = token_manager.verify_token(refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    
    # Verificar se usuário ainda existe e está ativo
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Gerar novos tokens
    tokens = token_manager.set_auth_cookies(response, user_id)
    
    return {
        "access_token": "refreshed_in_cookie",
        "token_type": "bearer",
        "csrf_token": tokens["csrf_token"]
    }


@router.get(
    "/me", 
    response_model=UserResponse, 
    summary="Get current user details",
    responses={401: {"description": "Could not validate credentials"}}
)
async def read_current_user(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Obter detalhes do usuário atual com verificação CSRF para operações futuras."""
    # Para GET não precisamos verificar CSRF, mas podemos retornar o token atual
    csrf_token = token_manager.get_csrf_token_from_cookie(request)
    
    # Adicionar CSRF token nos headers da resposta para conveniência
    response_data = current_user.dict() if hasattr(current_user, 'dict') else current_user.__dict__
    response_data["csrf_token"] = csrf_token
    
    return response_data


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
