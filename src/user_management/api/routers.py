from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.application.privacy import masked_email
from src.user_management.api.dependencies import (
    get_current_user,
    get_login_throttle,
)
from src.user_management.application.dtos import CreateUserCommand
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.services.login_throttle import LoginThrottle
from src.user_management.application.services.user_service import UserService
from src.user_management.domain.errors import (
    InvalidCredentialsError,
)
from src.user_management.domain import User, UserRole

from src.user_management.application.services.account_email_service import AccountEmailService

from .dependencies import get_account_email_service, get_auth_service, get_auth_settings, get_user_service
from .schemas import (
    AuthOptionsResponse,
    ChangePasswordRequest,
    EmailRequest,
    PasswordResetRequest,
    RegisterResponse,
    TokenAction,
    ScopedTokenRequest,
    ScopedTokenResponse,
    UserCreate,
    UserResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserCreate,
    account_emails: AccountEmailService = Depends(get_account_email_service),
):
    """Cria a conta. Com o envio de e-mails ligado, ela só entra depois de
    confirmar o e-mail (email_verification_required)."""
    # Conflito (409) e dados inválidos (400) saem pelos tratadores globais.
    command = CreateUserCommand(email=user_data.email, password=user_data.password, role=UserRole.USER)
    user, verification_required = await account_emails.register(command)
    return RegisterResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        role=user.role.value,
        email_verification_required=verification_required,
    )


@router.get("/options", response_model=AuthOptionsResponse, summary="Opções da conta (envio de e-mails ligado?)")
async def auth_options(account_emails: AccountEmailService = Depends(get_account_email_service)):
    return AuthOptionsResponse(email_enabled=account_emails.enabled)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT, summary="Confirmar o e-mail pelo link recebido")
async def verify_email(
    payload: TokenAction, account_emails: AccountEmailService = Depends(get_account_email_service)
) -> Response:
    await account_emails.confirm_email(payload.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(
    payload: EmailRequest, account_emails: AccountEmailService = Depends(get_account_email_service)
):
    """Mesma resposta com ou sem conta: não revela quem está cadastrado."""
    await account_emails.resend_verification(payload.email)
    return {"message": "Se houver uma conta aguardando confirmação, enviamos um novo link."}


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: EmailRequest, account_emails: AccountEmailService = Depends(get_account_email_service)
):
    """Mesma resposta com ou sem conta: não revela quem está cadastrado."""
    await account_emails.request_password_reset(payload.email)
    return {"message": "Se houver uma conta com este e-mail, enviamos um link para criar uma nova senha."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT, summary="Definir nova senha pelo link recebido")
async def reset_password(
    payload: PasswordResetRequest, account_emails: AccountEmailService = Depends(get_account_email_service)
) -> Response:
    await account_emails.reset_password(payload.token, payload.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _client_ip(request: Request) -> Optional[str]:
    """IP do cliente. Atrás do Nginx, usa o X-Real-IP definido pelo proxy."""
    forwarded = request.headers.get("x-real-ip")
    if forwarded:
        return forwarded.strip()
    return request.client.host if request.client else None


@router.post("/token", summary="Entrar (e-mail e senha)")
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
        logger.warning("auth.login.throttled", email=masked_email(form_data.username), ip=client_ip)
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
    except InvalidCredentialsError:
        await throttle.register_failure(form_data.username, client_ip)
        raise  # 401 pelo tratador global

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


@router.post("/refresh", summary="Renovar a sessão pelo cookie de renovação")
async def refresh_token(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    settings=Depends(get_auth_settings),
):
    refresh_cookie = request.cookies.get("refresh_token")
    if not refresh_cookie:
        raise InvalidCredentialsError("Sessão expirada; entre de novo.")
    tokens = await auth_service.refresh(refresh_cookie)  # inválido ou revogado: 401
    new_access, new_refresh = tokens["access_token"], tokens["refresh_token"]

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
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Revoga o token de renovação e apaga o cookie."""
    await auth_service.logout(request.cookies.get("refresh_token"))
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logout realizado"}


@router.post("/scoped-token", response_model=ScopedTokenResponse)
async def issue_scoped_token(
    payload: ScopedTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends(get_auth_service),
):
    """Token de finalidade restrita para onde o navegador não manda cabeçalho:
    a URL do vídeo (por mídia) e a abertura do WebSocket de avisos."""
    return auth_service.issue_scoped_token(current_user, payload.purpose, payload.resource)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserService = Depends(get_user_service),
) -> Response:
    """Troca a senha do usuário logado, exigindo a senha atual."""
    await user_service.change_password(current_user.id, payload.old_password, payload.new_password)
    logger.info("auth.password_changed", user_id=str(current_user.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse, summary="Usuário da sessão")
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    # Explicit mapping from Domain Entity -> DTO
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role.value,
    )
