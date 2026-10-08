"""SQLAlchemy model for User persistence."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, String, Uuid, true

from src.shared.infrastructure.database.db import Base
from src.shared.infrastructure.database.types import enum_column
from src.user_management.domain.entities.user import User as DomainUser
from src.user_management.domain.entities.user import UserRole


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=True, server_default=true(), nullable=False)
    role = Column(
        enum_column(UserRole),
        default=UserRole.USER,
        nullable=False,
    )

    def to_domain(self) -> DomainUser:
        """Convert persistence model to domain entity."""
        return DomainUser(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            is_active=self.is_active,
            role=self.role,
            email_verified=self.email_verified,
        )

    @classmethod
    def from_domain(cls, user: DomainUser) -> "UserModel":
        """Create persistence model from domain entity."""
        return cls(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
            role=user.role,
            email_verified=user.email_verified,
        )
