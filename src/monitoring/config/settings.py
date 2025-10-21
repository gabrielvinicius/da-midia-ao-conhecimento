from pydantic_settings import BaseSettings

class AnalyticsSettings(BaseSettings):
    default_transcription_factor: float = 0.1
    default_summarization_seconds: float = 60.0
    high_confidence_threshold: int = 100

    class Config:
        env_prefix = "ANALYTICS_"
        case_sensitive = False

