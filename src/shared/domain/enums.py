from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    SERVICE_ACCOUNT = "service_account"