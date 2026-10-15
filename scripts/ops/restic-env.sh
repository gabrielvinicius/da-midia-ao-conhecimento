# Configuração comum de backup.sh, restore.sh e verify-backup.sh (incluído
# com "."). Lê o .env da pasta do projeto e define a função restic, que roda
# o restic num contêiner com o repositório e a chave.
# shellcheck shell=sh
# shellcheck disable=SC2034 # variáveis usadas pelos scripts que incluem este.

export MSYS_NO_PATHCONV=1  # Git Bash (Windows): não converter /repo, /dados...
RESTIC_IMAGE=restic/restic:0.19.1

# ENV_FILE: outro arquivo de variáveis (testes); o padrão é o .env da pasta.
env_value() { grep -E "^$1=" "${ENV_FILE:-.env}" | tail -n 1 | cut -d= -f2- || true; }

REPOSITORY="$(env_value BACKUP_REPOSITORY)"
RESTIC_PASSWORD="$(env_value BACKUP_PASSWORD)"
[ -n "$REPOSITORY" ] || { echo "defina BACKUP_REPOSITORY no .env" >&2; exit 1; }
[ -n "$RESTIC_PASSWORD" ] || { echo "defina BACKUP_PASSWORD no .env" >&2; exit 1; }
export RESTIC_PASSWORD
DB_USER="$(env_value DB_USER)"
DB_NAME="$(env_value DB_NAME)"

# Pasta do host (C:/backups/restic, /srv/backups) é montada no contêiner;
# destinos remotos do restic (s3:..., b2:..., rclone:...) vão como estão.
case "$REPOSITORY" in
  [A-Za-z]:/*|[A-Za-z]:\\*|/*)
    mkdir -p "$REPOSITORY" 2>/dev/null || true
    REPO_MOUNT="-v $REPOSITORY:/repo"; RESTIC_REPOSITORY=/repo ;;
  *) REPO_MOUNT=""; RESTIC_REPOSITORY="$REPOSITORY" ;;
esac
export RESTIC_REPOSITORY

# Mídias: a pasta do host em MEDIA_STORAGE_PATH ou o volume do Compose.
MEDIA_SOURCE="$(env_value MEDIA_STORAGE_PATH)"
if [ -z "$MEDIA_SOURCE" ]; then
  MEDIA_SOURCE="$(docker compose config --format json | grep -o '"name": *"[^"]*_media_data"' | head -n 1 | sed 's/.*"\([^"]*\)"$/\1/')"
fi
[ -n "$MEDIA_SOURCE" ] || { echo "origem das mídias não encontrada" >&2; exit 1; }

# Uso: restic [opções do docker run] "$RESTIC_IMAGE" <comando do restic>
# shellcheck disable=SC2086 # REPO_MOUNT é vazio ou "-v origem:/repo".
restic() {
  docker run --rm -i --hostname producao -e RESTIC_PASSWORD -e RESTIC_REPOSITORY $REPO_MOUNT "$@"
}
