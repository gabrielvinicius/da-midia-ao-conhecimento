# src/diarization/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class DiarizationSettings(BaseSettings):
    """Configuration settings for the diarization module."""
    # To get a token, visit https://huggingface.co/settings/tokens
    hf_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')
