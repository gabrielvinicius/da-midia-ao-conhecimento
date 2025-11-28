import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from src.user_management.domain.user import User, UserRole

class TestUserDomain:
    def test_create_user(self):
        email = "test@example.com"
        password_hash = "hashed_secret"
        
        user = User.create(email=email, password_hash=password_hash)
        
        assert user.id is not None
        assert user.email == email
        assert user.password_hash == password_hash
        assert user.role == UserRole.USER
        assert user.is_active is True

    def test_create_admin_user(self):
        user = User.create(
            email="admin@example.com", 
            password_hash="secret", 
            role=UserRole.ADMIN
        )
        
        assert user.role == UserRole.ADMIN

    def test_user_equality(self):
        # Dataclasses define equality by value. 
        # For entities, typically identity is defined by ID, but dataclass default is all fields.
        # Since we generate random IDs in create(), we check manual instantiation.
        uid = uuid4()
        user1 = User(id=uid, email="a@b.com", password_hash="x", role=UserRole.USER, is_active=True)
        user2 = User(id=uid, email="a@b.com", password_hash="x", role=UserRole.USER, is_active=True)
        
        assert user1 == user2
