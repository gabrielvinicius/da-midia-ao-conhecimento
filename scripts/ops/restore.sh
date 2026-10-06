#!/bin/sh
# Restaura uma cópia feita por backup.sh (substitui o banco e as mídias atuais).
# Uso, na pasta do projeto, com o postgres no ar:
#   sh scripts/ops/restore.sh backups/<data>
set -eu

SRC="${1:?informe a pasta da cópia, ex.: backups/20261006-120000}"
DB_USER="$(grep -E '^DB_USER=' .env | cut -d= -f2-)"
DB_NAME="$(grep -E '^DB_NAME=' .env | cut -d= -f2-)"
# Volume das mídias, achado pelos rótulos do Compose (não exige o backend no ar).
PROJECT="$(docker compose config | sed -n 's/^name: //p')"
MEDIA_VOLUME="$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT" \
  --filter label=com.docker.compose.volume=media_data)"
[ -n "$MEDIA_VOLUME" ] || { echo "volume media_data do projeto $PROJECT não encontrado" >&2; exit 1; }

echo "[restore] parando os workers durante a restauração"
docker compose stop worker-heavy worker-light

echo "[restore] banco <- $SRC/banco.sql.gz"
gunzip -c "$SRC/banco.sql.gz" | docker compose exec -T postgres \
  psql -q -v ON_ERROR_STOP=1 -U "${DB_USER:-postgres}" -d "${DB_NAME:-video_summarizer}"

echo "[restore] mídias <- $SRC/midias.tar.gz"
docker run --rm -v "$MEDIA_VOLUME":/dados \
  -v "$(cd "$SRC" && pwd)":/origem:ro alpine sh -c 'rm -rf /dados/* && tar xzf /origem/midias.tar.gz -C /dados'

docker compose start worker-heavy worker-light
echo "[restore] pronto"
