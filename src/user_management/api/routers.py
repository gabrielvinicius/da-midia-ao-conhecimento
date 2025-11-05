from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.shared.api.dependencies import get_current_admin_user, get_current_user
from src.user_management.application.auth_service import AuthService
from src.user_management.application.user_service import UserService
from src.user_management.domain.user import User

from .dependencies import get_auth_service, get_user_service
from .schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    try:
        result = await user_service.register_user(user_data.email, user_data.password)
        return result["user"]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        result = await auth_service.authenticate_user(form_data.username, form_data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    return {"access_token": result["token"], "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(get_current_admin_user)])
async def list_all_users(user_service: UserService = Depends(get_user_service)):
    return await user_service.list_users()

