from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from src.user_management.api.dependencies import get_current_admin_user, get_current_user
from src.user_management.application.auth_service import AuthService
from src.user_management.application.user_service import UserService
from src.user_management.domain.user import User
from src.user_management.domain.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidCredentialsError
)

from .dependencies import get_auth_service, get_auth_settings, get_user_service
from .schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    try:
        result = await user_service.register_user(user_data.email, user_data.password)
        # Explicitly map domain dict to DTO (though register_user returns a dict, ideal would be User entity)
        # user_service.register_user returns {"success": True, "user": {...}}
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
    try:
        result = await auth_service.authenticate_user(form_data.username, form_data.password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ValueError as e:
        # Catch-all for other value errors, but domain exceptions should cover logic
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    cookie_secure = settings.cookie_secure
    cookie_samesite = settings.cookie_samesite
    if cookie_samesite == "none" and not cookie_secure:
        cookie_samesite = "lax"

    response.set_cookie(
        key="access_token_cookie",
        value=result["token"],
        httponly=True,
        samesite=cookie_samesite,
        secure=cookie_secure,
    )
    return {
        "message": "Authentication successful",
        "access_token": result["token"],
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    # Explicit mapping from Domain Entity -> DTO
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role.value 
    )


@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(get_current_admin_user)])
async def list_all_users(user_service: UserService = Depends(get_user_service)):
    users = await user_service.list_users()
    # Explicit mapping list comprehension
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            is_active=u.is_active,
            role=u.role.value
        ) for u in users
    ]