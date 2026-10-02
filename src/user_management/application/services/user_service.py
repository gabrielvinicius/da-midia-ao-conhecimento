from __future__ import annotations

from typing import Any, Optional, Sequence
from uuid import UUID

from src.user_management.application.ports import (
    PasswordHasherPort,
    TokenProviderPort,
    UserRepositoryPort,
    UserDataEraserPort,
)
from src.user_management.config.settings import UserSettings, user_settings
from src.user_management.domain.errors import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.user_management.domain import User, UserRole

from ..dtos import (
    CreateUserCommand,
    DeleteUserCommand,
    GetUserQuery,
    UpdateUserCommand,
)
from src.user_management.application.auth_queries import UserReadService


class UserService:
    """Unified user service for command operations."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        user_read_service: UserReadService,
        password_hasher: PasswordHasherPort,
        token_provider: TokenProviderPort,
        settings: Optional[UserSettings] = None,
        data_erasers: Sequence[UserDataEraserPort] = (),
    ) -> None:
        self.user_repository = user_repository
        self.user_read_service = user_read_service
        self.password_hasher = password_hasher
        self.token_provider = token_provider
        self.settings = settings or user_settings
        self.data_erasers = list(data_erasers)

    async def create_user(self, command: CreateUserCommand) -> User:
        await self._ensure_email_available(command.email)
        self._validate_password_strength(command.password)
        normalised_role = (
            command.role
            if isinstance(command.role, UserRole)
            else self._normalise_role(str(command.role))
        )

        user = User.create(
            email=command.email,
            password_hash=self.password_hasher.hash(
                command.password[:72]
            ),  # bcrypt limit
            role=normalised_role,
        )
        return await self.user_repository.save(user)

    async def register_user(self, command: CreateUserCommand) -> dict[str, object]:
        user = await self.create_user(command)
        return {
            "success": True,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            },
        }

    async def update_user(self, command: UpdateUserCommand) -> User:
        if (
            not command.email
            and not command.password
            and not command.role
            and command.is_active is None
        ):
            raise ValueError("Nenhuma atualização fornecida")

        user = await self._get_or_raise(command.user_id)

        if command.email:
            self._validate_email_format(command.email)
            if command.email != user.email:
                await self._ensure_email_available(command.email)
            user.email = command.email

        if command.role:
            user.role = self._normalise_role(command.role.value)

        if command.is_active is not None:
            user.is_active = command.is_active

        if command.password:
            self._validate_password_strength(command.password)
            user.password_hash = self.password_hasher.hash(command.password)

        return await self.user_repository.save(user)

    async def delete_user(self, command: DeleteUserCommand) -> None:
        """Apaga o que cada módulo guarda do usuário e depois a conta.

        Antes, só a conta era apagada: as chaves estrangeiras das mídias e dos
        avisos barravam a exclusão (erro 500) de quem já tinha enviado algo.
        Cada módulo apaga os próprios dados (as mídias levam arquivos,
        transcrições e análises); se algo falhar, a conta fica e a exclusão
        pode ser repetida.
        """
        await self._get_or_raise(command.user_id)
        for eraser in self.data_erasers:
            await eraser.erase(command.user_id)
        if not await self.user_repository.delete(command.user_id):
            raise ValueError("Usuário não pôde ser removido")

    async def activate_user(self, command: GetUserQuery) -> User:
        user = await self._get_or_raise(command.user_id)
        user.is_active = True
        return await self.user_repository.save(user)

    async def deactivate_user(self, command: GetUserQuery) -> User:
        user = await self._get_or_raise(command.user_id)
        user.is_active = False
        return await self.user_repository.save(user)

    async def change_password(
        self, user_id: UUID, old_password: str, new_password: str
    ) -> None:
        user = await self._get_or_raise(user_id)
        if not self.password_hasher.verify(old_password, user.password_hash):
            raise InvalidCredentialsError()
        self._validate_password_strength(new_password)
        user.password_hash = self.password_hasher.hash(new_password)
        await self.user_repository.save(user)

    async def ensure_admin_user(
        self,
        *,
        email: str,
        default_password: str,
        force_password_reset: bool = False,
    ) -> User:
        normalised_email = email.strip().lower()
        if not normalised_email:
            raise ValueError("Email do admin não pode ser vazio")

        self._validate_password_strength(default_password)

        existing = await self.user_read_service.get_user_by_email(normalised_email)
        if existing is None:
            return await self.create_user(
                CreateUserCommand(
                    email=normalised_email,
                    password=default_password,
                    role=UserRole.ADMIN,
                )
            )

        updated = False
        if existing.role != UserRole.ADMIN:
            existing.role = UserRole.ADMIN
            updated = True

        if force_password_reset:
            existing.password_hash = self.password_hasher.hash(default_password[:72])
            updated = True

        if updated:
            return await self.user_repository.save(existing)

        return existing

    async def authenticate_user(
        self, email: str, password: str
    ) -> dict[str, Any]:
        user = await self.user_read_service.get_user_by_email(email)
        if user is None or not self.password_hasher.verify(
            password, user.password_hash
        ):
            raise InvalidCredentialsError()
        if not user.is_active:
            # A senha confere; dizer que a conta está desativada não expõe nada.
            raise InvalidCredentialsError("Conta desativada")
        access_token = self.token_provider.create_access_token(user.id)
        refresh_token = self.token_provider.create_refresh_token(user.id)
        return {
            "token": access_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            },
        }

    async def _get_or_raise(self, user_id: UUID) -> User:
        user = await self.user_read_service.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        return user

    def _validate_email_format(self, email: str) -> None:
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Formato de email inválido")

    async def _ensure_email_available(self, email: str) -> None:
        existing = await self.user_read_service.get_user_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(email)

    def _validate_password_strength(self, password: str) -> None:
        min_length = self.settings.auth_password_min_length
        if len(password) < min_length:
            raise ValueError(f"Senha deve ter pelo menos {min_length} caracteres")
        if not any(c.isupper() for c in password):
            raise ValueError("Senha deve conter ao menos uma letra maiúscula")
        if not any(c.islower() for c in password):
            raise ValueError("Senha deve conter ao menos uma letra minúscula")
        if not any(c.isdigit() for c in password):
            raise ValueError("Senha deve conter ao menos um número")

    def _normalise_role(self, role: str) -> UserRole:
        try:
            return UserRole(role.upper())
        except ValueError:
            valid = ", ".join(r.value for r in UserRole)
            raise ValueError(f"Perfil inválido. Perfis válidos: {valid}") from None
