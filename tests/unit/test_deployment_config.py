"""Configuração de implantação: o que o .env.example documenta é lido de fato,
e a produção não oferece o transcritor de mentira."""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _settings_env_names() -> set[str]:
    """Nomes de variável aceitos pelas classes de configuração (com prefixo)."""
    from src.media_management.config.settings import MediaSettings
    from src.media_processing.config.settings import MediaProcessingSettings
    from src.shared.infrastructure.config.settings import Settings
    from src.storage.config.settings import StorageSettings
    from src.user_management.config.settings import UserSettings

    names = set()
    for cls in (Settings, MediaSettings, MediaProcessingSettings, StorageSettings, UserSettings):
        prefix = (cls.model_config.get("env_prefix") or "").upper()
        for name, field in cls.model_fields.items():
            names.add(prefix + name.upper())
            alias = field.validation_alias
            for choice in getattr(alias, "choices", []) or []:
                names.add(str(choice).upper())
    return names


# Lidas fora das classes de configuração (compose, bibliotecas, entrypoints).
READ_ELSEWHERE = {
    "DB_SCHEME", "DB_USER", "DB_PASSWORD", "DB_NAME",  # docker-compose monta DATABASE_URL
    "CELERY_BROKER_URL",  # src/celery_app.py
    "HF_TOKEN",  # biblioteca da Hugging Face
    "OTEL_EXPORTER_OTLP_ENDPOINT",  # OpenTelemetry
    "LOG_FORMAT", "LOG_LEVEL", "METRICS_PORT",  # observabilidade
    "DEFAULT_ADMIN_EMAIL", "DEFAULT_ADMIN_PASSWORD", "DEFAULT_ADMIN_FORCE_PASSWORD",  # main.py
}


def test_every_variable_in_env_example_is_read():
    """Antes, ACCESS_TOKEN_EXPIRE_MINUTES=60 e ALGORITHM estavam no exemplo, mas
    o nome lido leva o prefixo USER_: o valor efetivo era outro, sem aviso."""
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", text, flags=re.M))
    unread = documented - _settings_env_names() - READ_ELSEWHERE
    assert not unread, f"variáveis do .env.example que nada lê: {sorted(unread)}"


def test_read_elsewhere_names_are_really_used():
    sources = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in [*ROOT.glob("src/**/*.py"), ROOT / "main.py", ROOT / "docker-compose.yml"]
    )
    library_reads = {"HF_TOKEN", "OTEL_EXPORTER_OTLP_ENDPOINT"}
    missing = {n for n in READ_ELSEWHERE - library_reads if n not in sources}
    assert not missing, f"nomes que o código não usa mais: {sorted(missing)}"


def test_production_does_not_offer_the_fake_transcriber():
    code = (
        "from src.media_processing.infrastructure.dependencies import providers as p;"
        "print('whisper' in p._SPEECH_RECOGNIZERS)"
    )
    env = {**os.environ, "APP_ENV": "production"}
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "False"


def test_an_unknown_transcription_provider_uses_the_real_default():
    from src.media_processing.infrastructure.dependencies import providers

    assert providers._SPEECH_RECOGNIZERS.get("default") is not None
    calls = []
    providers.register_speech_recognizer("teste-padrao", lambda: calls.append(1) or "ok", public=False)
    original = providers._SPEECH_RECOGNIZERS["default"]
    providers._SPEECH_RECOGNIZERS["default"] = providers._SPEECH_RECOGNIZERS["teste-padrao"]
    try:
        assert providers.get_speech_recognizer("nao-existe") == "ok"
    finally:
        providers._SPEECH_RECOGNIZERS["default"] = original
        providers._SPEECH_RECOGNIZERS.pop("teste-padrao")
        providers._SPEECH_META.pop("teste-padrao")
