#!/bin/sh
# Restaura uma cópia feita por backup.sh: substitui o banco e as mídias atuais.
# Uso, na pasta do projeto, com o postgres no ar:
#   sh scripts/ops/restore.sh            (a cópia mais recente)
#   sh scripts/ops/restore.sh <snapshot> (ids em: restic snapshots)
# O banco volta pelo pg_restore; as mídias, pelo restic (arquivos que não
# estavam na cópia são apagados), e também as do S3 local (Garage), quando a
# cópia as tem. Os workers ficam parados durante a operação.
set -eu
. scripts/ops/restic-env.sh

SNAPSHOT="${1:-latest}"
DUMP="$(mktemp)"
trap 'rm -f "$DUMP"; docker compose start worker-heavy worker-light >/dev/null 2>&1 || true' EXIT

echo "[restore] conferindo a cópia ($SNAPSHOT)"
restic "$RESTIC_IMAGE" dump --tag banco "$SNAPSHOT" banco.dump > "$DUMP"
[ -s "$DUMP" ] || { echo "a cópia do banco está vazia" >&2; exit 1; }

echo "[restore] parando os workers"
docker compose stop worker-heavy worker-light

echo "[restore] banco ${DB_NAME:-app}"
docker compose exec -T postgres pg_restore -U "${DB_USER:-postgres}" -d "${DB_NAME:-app}" \
  --clean --if-exists --no-owner --exit-on-error < "$DUMP"

echo "[restore] mídias ($MEDIA_SOURCE)"
# O --include é exigido pelo restic com --target / e --delete: sem ele, a
# restauração das mídias falhava ("must be combined with an include or exclude
# filter") e só o banco voltava.
restic -v "$MEDIA_SOURCE:/dados/midias" "$RESTIC_IMAGE" restore "$SNAPSHOT" --tag midias \
  --target / --include /dados/midias --overwrite always --delete

if [ -n "$S3_SOURCE" ] && restic "$RESTIC_IMAGE" snapshots --tag s3 --json | grep -q '"id"'; then
  echo "[restore] S3 local, Garage ($S3_SOURCE)"
  # Como manda a documentação do Garage: parado, os dados e as cópias do banco
  # voltam, a cópia mais recente vira o banco, e um reparo ao subir acerta o
  # que mudou depois dela.
  docker compose stop garage >/dev/null 2>&1 || true
  restic -v "$S3_SOURCE:/dados/s3" "$RESTIC_IMAGE" restore "$SNAPSHOT" --tag s3 \
    --target / --include /dados/s3 --overwrite always --delete
  # Na v2.4, cada cópia é uma pasta (snapshots/<data>/db.sqlite).
  docker run --rm --entrypoint sh -v "$S3_SOURCE:/dados/s3" "$RESTIC_IMAGE" -ec '
    cd /dados/s3/meta
    ultima="$(ls -1 snapshots | sort | tail -n 1)"
    [ -n "$ultima" ] || { echo "a cópia não tem o banco de metadados do Garage" >&2; exit 1; }
    origem="snapshots/$ultima"; [ -d "$origem" ] && origem="$origem/db.sqlite"
    rm -f db.sqlite db.sqlite-wal db.sqlite-shm
    cp "$origem" db.sqlite
    echo "[restore] banco de metadados do Garage: $ultima"'
  if docker compose start garage >/dev/null 2>&1; then
    i=0
    until garage_running && docker compose exec -T garage /garage status >/dev/null 2>&1; do
      i=$((i + 1)); [ "$i" -le 30 ] || { echo "o Garage não voltou" >&2; exit 1; }
      sleep 2
    done
    docker compose exec -T garage /garage repair -a --yes tables
  fi
fi

echo "[restore] pronto"
