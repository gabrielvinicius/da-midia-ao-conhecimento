from pydantic_settings import BaseSettings, SettingsConfigDict


class UserSettings(BaseSettings):
    """User/Auth bounded-context settings."""

    secret_key: str = "insecure-secret-key-for-dev"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    auth_password_min_length: int = 8
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    lightweight_mode: bool = False

    model_config = SettingsConfigDict(
        env_prefix="USER_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Compat for legacy uppercase attribute names
    @property
    def SECRET_KEY(self) -> str:  # pragma: no cover - simple alias  # noqa: N802
        return self.secret_key

    @property
    def ALGORITHM(self) -> str:  # pragma: no cover  # noqa: N802
        return self.algorithm

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:  # pragma: no cover  # noqa: N802
        return self.access_token_expire_minutes


user_settings = UserSettings()


__all__ = ["UserSettings", "user_settings"]
