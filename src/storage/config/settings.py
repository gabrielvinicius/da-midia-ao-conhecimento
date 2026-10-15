from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    """Storage bounded-context settings."""

    providers_allowed: List[str] = ["local", "s3"]

    # Serviço compatível com S3. Sem bucket, a opção "s3" não é oferecida.
    # O endpoint fica vazio na AWS; no perfil "s3" do Compose, é o Garage local.
    s3_endpoint_url: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_region: str = "us-east-1"

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def s3_configured(self) -> bool:
        return bool(self.s3_bucket)


storage_settings = StorageSettings()


__all__ = ["StorageSettings", "storage_settings"]
