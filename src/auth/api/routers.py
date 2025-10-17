# src/auth/api/routers.py
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm

# Import dependencies from their correct, decoupled locations
from .dependencies import get_user_registration_service, get_authentication_service, get_auth_queries
from src.shared.api.dependencies import get_current_user, get_current_admin_user

from .schemas import Token, UserResponse, UserCreate, TokenRequest
from src.auth.application.services.user_registration_service import UserRegistrationService
from src.auth.application.services.authentication_service import AuthenticationService
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.domain.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    registration_service: UserRegistrationService = Depends(get_user_registration_service),
):
    try:
        return await registration_service.register_user(user_data.email, user_data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    authentication_service: AuthenticationService = Depends(get_authentication_service),
):
    token = await authentication_service.authenticate(form_data.username, form_data.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(get_current_admin_user)])
async def list_all_users(auth_queries: AuthQueries = Depends(get_auth_queries)):
    return await auth_queries.list_all()
