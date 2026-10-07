#!/bin/sh
# Cópia de segurança do banco e das mídias enviadas (armazenamento local).
# Uso, na pasta do projeto, com o sistema no ar:
#   sh scripts/ops/backup.sh [pasta-de-destino]
# Gera <destino>/<data>/banco.sql.gz e midias.tar.gz. O MinIO e os modelos de
# IA não entram: os modelos são baixados de novo, e o bucket do MinIO, se
# usado, deve ser copiado à parte (mc mirror).
set -eu

DEST="${1:-backups}/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST"
DB_USER="$(grep -E '^DB_USER=' .env | cut -d= -f2-)"
DB_NAME="$(grep -E '^DB_NAME=' .env | cut -d= -f2-)"
# Volume das mídias, achado pelos rótulos do Compose (não exige o backend no ar).
PROJECT="$(docker compose config | sed -n 's/^name: //p')"
MEDIA_VOLUME="$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT" \
  --filter label=com.docker.compose.volume=media_data)"
[ -n "$MEDIA_VOLUME" ] || { echo "volume media_data do projeto $PROJECT não encontrado" >&2; exit 1; }

echo "[backup] banco ${DB_NAME:-video_summarizer} -> $DEST/banco.sql.gz"
docker compose exec -T postgres pg_dump -U "${DB_USER:-postgres}" -d "${DB_NAME:-video_summarizer}" \
  --clean --if-exists | gzip > "$DEST/banco.sql.gz"

echo "[backup] mídias -> $DEST/midias.tar.gz"
# MSYS_NO_PATHCONV e pwd -W: no Git Bash (Windows), os caminhos do contêiner
# não podem ser convertidos (ver restore.sh).
MSYS_NO_PATHCONV=1 docker run --rm -v "$MEDIA_VOLUME":/dados:ro \
  -v "$(cd "$DEST" && (pwd -W 2>/dev/null || pwd))":/destino alpine tar czf /destino/midias.tar.gz -C /dados .

echo "[backup] pronto: $DEST"
