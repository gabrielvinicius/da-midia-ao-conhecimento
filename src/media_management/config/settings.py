from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class MediaSettings(BaseSettings):
    """Media-management specific settings."""

    storage_providers_allowed: List[str] = ["local", "s3"]
    # Nomes do catálogo de transcrição (media_processing); um nome fora da
    # lista só gera aviso, e o worker usa o padrão.
    transcription_providers_allowed: List[str] = ["default", "fastwhisper", "openai-whisper"]
    media_min_file_size_bytes: int = 1
    media_max_file_size_bytes: int = 500 * 1024 * 1024
    # Envio em partes (a Cloudflare recusa requisições acima de 100 MB): maior
    # parte aceita, pasta dos envios em andamento (vazia: a temporária do
    # sistema) e horas até um envio abandonado ser apagado.
    media_upload_part_max_bytes: int = 64 * 1024 * 1024
    media_upload_staging_dir: str = ""
    media_upload_staging_hours: float = 24
    media_allowed_audio_extensions: List[str] = [
        "mp3",
        "wav",
        "flac",
        "aac",
        "ogg",
        "m4a",
    ]
    media_allowed_video_extensions: List[str] = [
        "mp4",
        "avi",
        "mov",
        "mkv",
        "webm",
        "flv",
    ]
    media_allowed_text_extensions: List[str] = [
        "txt",
        "pdf",
        "docx",
        "png",
        "jpg",
        "jpeg",
        "tiff",
        "bmp",
    ]

    # Importação de vídeos por link do YouTube (MEDIA_URL_IMPORT_ENABLED).
    media_url_import_enabled: bool = True
    media_url_import_max_minutes: int = 240

    # Mídia enviada sem registro de processamento (UnstartedMediaRecovery):
    # anunciada de novo após a folga e marcada como falha após o limite.
    unstarted_check_interval_seconds: int = 300
    unstarted_grace_minutes: float = 10
    unstarted_give_up_minutes: float = 60
    # Mídia "em análise" há mais que isto: o worker da análise morreu sem
    # anunciar a falha (UnfinishedAnalysisRecovery). A análise de uma aula de
    # duas horas leva minutos; o limite só pega o que parou de vez.
    analysis_give_up_minutes: float = 180

    model_config = SettingsConfigDict(
        env_prefix="MEDIA_",
        case_sensitive=False,
        extra="ignore",
    )


media_settings = MediaSettings()


__all__ = ["MediaSettings", "media_settings"]
