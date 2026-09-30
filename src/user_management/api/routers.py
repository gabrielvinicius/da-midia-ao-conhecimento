from typing import Annotated, Optional

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

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.user_management.api.dependencies import (
    get_current_admin_user,
    get_current_user,
    get_login_throttle,
)
from src.user_management.application.dtos import CreateUserCommand, ListUsersQuery
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.services.login_throttle import LoginThrottle
from src.user_management.application.services.user_service import UserService
from src.user_management.domain.errors import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from src.user_management.domain import User, UserRole
from src.user_management.config.settings import user_settings

from .dependencies import get_auth_service, get_auth_settings, get_user_service
from .schemas import ChangePasswordRequest, UserCreate, UserResponse

logger = get_logger(__name__)

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
    try:
        command = CreateUserCommand(
            email=user_data.email,
            password=user_data.password,
            role=UserRole.USER,
        )
        result = await user_service.register_user(command)
        return UserResponse(**result["user"])
    except UserAlreadyExistsError as e:
        logger.warning("auth.register.conflict", email=user_data.email, error=str(e))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        logger.warning("auth.register.validation_error", email=user_data.email, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _client_ip(request: Request) -> Optional[str]:
    """IP do cliente. Atrás do Nginx, usa o X-Real-IP definido pelo proxy."""
    forwarded = request.headers.get("x-real-ip")
    if forwarded:
        return forwarded.strip()
    return request.client.host if request.client else None


@router.post("/token")
async def login_for_access_token(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
    settings=Depends(get_auth_settings),
    throttle: LoginThrottle = Depends(get_login_throttle),
):
    client_ip = _client_ip(request)
    wait = await throttle.retry_after(form_data.username, client_ip)
    if wait > 0:
        logger.warning("auth.login.throttled", email=form_data.username, ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas de login. Tente novamente em {max(1, wait // 60)} minuto(s).",
            headers={"Retry-After": str(wait)},
        )
    try:
        result = await auth_service.authenticate_user(
            form_data.username,
            form_data.password,
        )
    except InvalidCredentialsError as e:
        await throttle.register_failure(form_data.username, client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ValueError as e:
        # Catch-all for other value errors, but domain exceptions should cover logic
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await throttle.register_success(form_data.username)

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


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserService = Depends(get_user_service),
) -> Response:
    """Troca a senha do usuário logado, exigindo a senha atual."""
    try:
        await user_service.change_password(
            current_user.id, payload.old_password, payload.new_password
        )
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")
    except ValueError as exc:  # regras de força da senha
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    logger.info("auth.password_changed", user_id=str(current_user.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    response_model=list[UserResponse],
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
