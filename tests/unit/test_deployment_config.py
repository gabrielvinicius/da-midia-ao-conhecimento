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
    "CLOUDFLARE_TUNNEL_TOKEN",  # docker-compose.yml, serviço cloudflared
    "MEDIA_STORAGE_PATH",  # docker-compose.yml, pasta das mídias no host
    "COMPOSE_PROFILES",  # lida pelo próprio docker compose (perfis opcionais)
    "BACKUP_REPOSITORY", "BACKUP_PASSWORD",  # scripts/ops/restic-env.sh
    "BACKUP_KEEP_DAILY", "BACKUP_KEEP_WEEKLY", "BACKUP_KEEP_MONTHLY",  # scripts/ops/backup.sh
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
        for p in [*ROOT.glob("src/**/*.py"), ROOT / "main.py", ROOT / "docker-compose.yml", *ROOT.glob("scripts/ops/*.sh")]
    )
    library_reads = {"HF_TOKEN", "OTEL_EXPORTER_OTLP_ENDPOINT", "COMPOSE_PROFILES"}
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


def _compose_project_name() -> str:
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    found = re.findall(r"^name:\s*(\S+)\s*$", text, flags=re.M)
    assert len(found) == 1, "docker-compose.yml deve declarar name: uma vez, no topo"
    return found[0]


def test_compose_project_name_is_declared_only_in_the_compose_file():
    """Antes, o nome estava em seis volumes e no deploy.ps1, e os scripts de
    cópia de segurança, sem ele, procuravam outro projeto na pasta de produção
    (e gravavam um banco vazio)."""
    project = _compose_project_name()
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert f"name: {project}_" not in compose, "volumes devem herdar o nome do projeto"
    others = [*ROOT.glob("scripts/**/*"), *ROOT.glob(".github/workflows/*.yml"), *ROOT.glob("docker-compose.*.yml")]
    repeated = [str(p.relative_to(ROOT)) for p in others
                if p.suffix in {".sh", ".ps1", ".py", ".yml"} and project in p.read_text(encoding="utf-8", errors="ignore")]
    assert not repeated, f"nome do projeto repetido fora do docker-compose.yml: {repeated}"


def test_deploy_workflow_takes_machine_values_from_repository_variables():
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    assert "${{ vars.DEPLOY_DIR }}" in workflow and "${{ vars.PUBLIC_URL }}" in workflow
    assert not re.search(r"[A-Z]:\\\\", workflow), "caminho da máquina de produção fixo no workflow"


def _compose_services() -> dict:
    import yaml

    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]


def test_every_service_rotates_logs_and_blocks_privilege_escalation():
    """O driver padrão (json-file) não rotaciona: os logs cresciam sem limite."""
    for name, service in _compose_services().items():
        assert service.get("logging", {}).get("driver") == "local", f"{name}: logs sem rotação"
        assert "no-new-privileges:true" in service.get("security_opt", []), f"{name}: sem no-new-privileges"


def test_every_image_has_a_fixed_version_and_no_container_name_is_fixed():
    """minio:latest quebrou a instalação quando a imagem deixou de ser publicada;
    container_name fixo impedia uma segunda instância (de teste) na máquina."""
    for name, service in _compose_services().items():
        image = service["image"]
        assert "@sha256:" in image or (":" in image and not image.endswith(":latest")), f"{name}: {image}"
        assert "container_name" not in service, f"{name}: container_name fixo"
