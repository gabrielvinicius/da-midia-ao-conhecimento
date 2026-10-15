#!/bin/sh
# Restaura uma cópia feita por backup.sh (substitui o banco e as mídias atuais).
# Uso, na pasta do projeto, com o postgres no ar:
#   sh scripts/ops/restore.sh backups/<data>
set -eu

SRC="${1:?informe a pasta da cópia, ex.: backups/20261006-120000}"
DB_USER="$(grep -E '^DB_USER=' .env | cut -d= -f2-)"
DB_NAME="$(grep -E '^DB_NAME=' .env | cut -d= -f2-)"
# Mídias: a pasta do host em MEDIA_STORAGE_PATH ou, sem ela, o volume pelo nome
# fixado no docker-compose.yml (não exige o backend no ar).
MEDIA_VOLUME="$(grep -E '^MEDIA_STORAGE_PATH=' .env | cut -d= -f2- || true)"
if [ -n "$MEDIA_VOLUME" ]; then
  [ -d "$MEDIA_VOLUME" ] || { echo "pasta das mídias ($MEDIA_VOLUME) não encontrada" >&2; exit 1; }
else
  MEDIA_VOLUME="$(docker compose config | sed -n '/^volumes:/,$p' | sed -n '/^  media_data:/{n;s/^ *name: //p;}')"
  docker volume inspect "$MEDIA_VOLUME" >/dev/null 2>&1 || { echo "volume das mídias ($MEDIA_VOLUME) não encontrado" >&2; exit 1; }
fi

echo "[restore] parando os workers durante a restauração"
docker compose stop worker-heavy worker-light

echo "[restore] banco <- $SRC/banco.sql.gz"
gunzip -c "$SRC/banco.sql.gz" | docker compose exec -T postgres \
  psql -q -v ON_ERROR_STOP=1 -U "${DB_USER:-postgres}" -d "${DB_NAME:-app}"

echo "[restore] mídias <- $SRC/midias.tar.gz"
# No Git Bash (Windows), sem MSYS_NO_PATHCONV o caminho do contêiner virava
# "C:/Program Files/Git/origem"; pwd -W dá o caminho que o Docker entende.
# O arquivo é conferido antes de apagar as mídias atuais.
MSYS_NO_PATHCONV=1 docker run --rm -v "$MEDIA_VOLUME":/dados \
  -v "$(cd "$SRC" && (pwd -W 2>/dev/null || pwd))":/origem:ro alpine sh -c \
  'tar tzf /origem/midias.tar.gz >/dev/null && rm -rf /dados/* && tar xzf /origem/midias.tar.gz -C /dados'

docker compose start worker-heavy worker-light
echo "[restore] pronto"
