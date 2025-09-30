# src/diarization/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field

class DiarizationSettings(BaseSettings):
    hf_token: str = Field(..., alias="HF_TOKEN", description="Hugging Face token for authenticated access to models like pyannote.")

    class Config:
        env_file = ".env"
        extra = "ignore"
