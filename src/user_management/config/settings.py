from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "insecure-secret-key-for-dev"
# Valores de exemplo que já apareceram no .env.example.
_PLACEHOLDER_SECRETS = {
    INSECURE_DEFAULT_SECRET,
    "a_very_strong_and_long_secret_key_should_be_placed_here",
    "troque-esta-chave",
}
MIN_SECRET_LENGTH = 32


class UserSettings(BaseSettings):
    """User/Auth bounded-context settings."""

    # Chave que assina os tokens JWT. Aceita USER_SECRET_KEY ou SECRET_KEY
    # (o nome usado no .env.example); antes só USER_SECRET_KEY era lida, e a
    # chave pública de desenvolvimento assinava os tokens sem aviso.
    secret_key: str = Field(
        default=INSECURE_DEFAULT_SECRET,
        validation_alias=AliasChoices("USER_SECRET_KEY", "SECRET_KEY"),
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7  # 7 dias
    # Tokens de finalidade restrita (application/tokens.py): o do reprodutor
    # cobre uma aula longa; o do WebSocket só precisa durar até conectar.
    stream_token_expire_minutes: int = 6 * 60
    socket_token_expire_seconds: int = 120
    auth_password_min_length: int = 8
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    lightweight_mode: bool = False
    # Proteção contra força bruta no login (janela e bloqueio em segundos)
    login_max_attempts_per_email: int = 5
    login_max_attempts_per_ip: int = 20
    login_block_seconds: int = 15 * 60

    # Endereço público da aplicação, usado nos links enviados por e-mail.
    public_url: str = Field(default="http://localhost:3000", validation_alias=AliasChoices("PUBLIC_URL", "USER_PUBLIC_URL"))
    # Envio de e-mails (confirmação do cadastro e nova senha). Opcional: sem
    # SMTP_HOST, o cadastro entra direto e a recuperação de senha não aparece.
    # Funciona com qualquer provedor SMTP (Resend, Brevo, Gmail, Amazon SES...).
    smtp_host: str = Field(default="", validation_alias=AliasChoices("SMTP_HOST"))
    smtp_port: int = Field(default=587, validation_alias=AliasChoices("SMTP_PORT"))
    smtp_username: str = Field(default="", validation_alias=AliasChoices("SMTP_USERNAME"))
    smtp_password: str = Field(default="", validation_alias=AliasChoices("SMTP_PASSWORD"))
    # Remetente, ex.: "Video Summarizer <no-reply@seudominio>".
    smtp_from: str = Field(default="", validation_alias=AliasChoices("SMTP_FROM"))
    # starttls (porta 587), ssl (465) ou none (servidor local de testes).
    smtp_security: str = Field(default="starttls", validation_alias=AliasChoices("SMTP_SECURITY"))
    email_verification_hours: int = 24
    password_reset_minutes: int = 60

    model_config = SettingsConfigDict(
        env_prefix="USER_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
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


def ensure_secure_secret(settings: UserSettings) -> None:
    """Impede a inicialização com uma chave de assinatura conhecida ou curta.

    Quem conhece a chave consegue gerar tokens válidos para qualquer usuário.
    """
    key = settings.secret_key or ""
    if key in _PLACEHOLDER_SECRETS or len(key) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            "SECRET_KEY ausente, de exemplo ou com menos de "
            f"{MIN_SECRET_LENGTH} caracteres. Gere uma chave com\n"
            '  python -c "import secrets; print(secrets.token_urlsafe(48))"\n'
            "e defina SECRET_KEY no arquivo .env."
        )
