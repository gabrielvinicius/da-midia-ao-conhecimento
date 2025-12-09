"""SQLAlchemy model for User persistence."""
from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, String, Uuid
from sqlalchemy import Enum as SQLAEnum
from sqlalchemy.orm import registry

from src.shared.infrastructure.database.db import Base
from src.user_management.domain.user import User as DomainUser, UserRole


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(SQLAEnum(UserRole, name="userrole"), default=UserRole.USER, nullable=False)

    def to_domain(self) -> DomainUser:
        """Convert persistence model to domain entity."""
        return DomainUser(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            is_active=self.is_active,
            role=self.role
        )

    @classmethod
    def from_domain(cls, user: DomainUser) -> "UserModel":
        """Create persistence model from domain entity."""
        return cls(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
            role=user.role
        )