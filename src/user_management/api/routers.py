import os
import json
import uuid
from typing import Annotated, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm

from src.user_management.api.dependencies import (
    get_current_admin_user,
    get_current_user,
)
from src.user_management.application.dtos import CreateUserCommand, ListUsersQuery
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.services.user_service import UserService
from src.user_management.domain.errors import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from src.user_management.domain import User
from src.user_management.config.settings import user_settings

from .dependencies import get_auth_service, get_auth_settings, get_user_service
from .schemas import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    logger.info("auth.register.received", email=user_data.email)
    # Atalho lightweight: retorna resposta imediata (evita dependências reais)
    if os.getenv("LIGHTWEIGHT_BOOTSTRAP") == "1" or os.getenv("USER_LIGHTWEIGHT_MODE") == "1":
        logger.info("auth.register.lightweight", email=user_data.email)
        payload = {
            "id": str(uuid.uuid4()),
            "email": user_data.email,
            "is_active": True,
            "role": "user",
        }
        return Response(
            content=json.dumps(payload),
            status_code=status.HTTP_201_CREATED,
            media_type="application/json",
        )
    try:
        command = CreateUserCommand(
            email=user_data.email,
            password=user_data.password,
            role=user_data.role,
        )
        result = await user_service.register_user(command)
        return UserResponse(**result["user"])
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/token")
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
    settings=Depends(get_auth_settings),
):
    if os.getenv("LIGHTWEIGHT_BOOTSTRAP") == "1" or os.getenv("USER_LIGHTWEIGHT_MODE") == "1":
        token = f"fake-token-{uuid.uuid4()}"
        response.set_cookie(
            key="access_token_cookie",
            value=token,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return {
            "message": "Authentication successful",
            "access_token": token,
            "token_type": "bearer",
        }
    try:
        result = await auth_service.authenticate_user(
            form_data.username,
            form_data.password,
        )
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ValueError as e:
        # Catch-all for other value errors, but domain exceptions should cover logic
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    cookie_secure = settings.cookie_secure
    cookie_samesite = settings.cookie_samesite
    if cookie_samesite == "none" and not cookie_secure:
        cookie_samesite = "lax"

    # Refresh token via cookie httpOnly; access token via body/header
    if result.get("refresh_token"):
        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            samesite=cookie_samesite,
            secure=cookie_secure,
            path="/",
        )
    return {
        "message": "Authentication successful",
        "access_token": result["access_token"],
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    settings=Depends(get_auth_settings),
):
    refresh_cookie = request.cookies.get("refresh_token")
    if not refresh_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token ausente")

    payload = auth_service.user_service.token_provider.verify_refresh_token(refresh_cookie)  # type: ignore[attr-defined]
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")

    user_id = payload["sub"]
    new_access = auth_service.user_service.token_provider.create_access_token(user_id)
    new_refresh = auth_service.user_service.token_provider.create_refresh_token(user_id)  # type: ignore[attr-defined]

    cookie_secure = settings.cookie_secure
    cookie_samesite = settings.cookie_samesite
    if cookie_samesite == "none" and not cookie_secure:
        cookie_samesite = "lax"

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
        path="/",
    )

    return {
        "message": "Token refresh bem-sucedido",
        "access_token": new_access,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(response: Response):
    """Remove refresh cookie no cliente."""
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("access_token_cookie", path="/")
    return {"message": "Logout realizado"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    # Explicit mapping from Domain Entity -> DTO
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role.value,
    )


@router.get(
    "/users",
    response_model=List[UserResponse],
    dependencies=[Depends(get_current_admin_user)],
)
async def list_all_users(
    user_service: UserService = Depends(get_user_service),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
):
    query = ListUsersQuery(page=page, limit=limit, search=search)
    users = await user_service.list_users(query)
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            is_active=u.is_active,
            role=u.role.value,
        )
        for u in users
    ]
