#!/bin/sh
# Teste de restauração: a cópia mais recente do banco é restaurada num
# PostgreSQL temporário, isolado da produção, e conferida com consultas.
# Uma cópia que nunca foi restaurada não é uma cópia confiável: este teste
# roda toda semana no workflow "Backup".
# Uso, na pasta do projeto:
#   sh scripts/ops/verify-backup.sh
set -eu
. scripts/ops/restic-env.sh

PG_IMAGE="$(docker compose config --format json | grep -o '"image": *"pgvector/[^"]*"' | head -n 1 | sed 's/.*"\([^"]*\)"$/\1/')"
NAME="verificacao-backup-$$"
DUMP="$(mktemp)"
trap 'rm -f "$DUMP"; docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

echo "[verify] mídias: leitura de 5% dos dados do repositório"
restic "$RESTIC_IMAGE" check --read-data-subset=5%

echo "[verify] banco: restauração num PostgreSQL temporário ($PG_IMAGE)"
restic "$RESTIC_IMAGE" dump --tag banco latest banco.dump > "$DUMP"
docker run -d --name "$NAME" -e POSTGRES_PASSWORD=verificacao -e POSTGRES_DB=verificacao "$PG_IMAGE" >/dev/null
i=0
until docker exec "$NAME" pg_isready -U postgres -d verificacao >/dev/null 2>&1; do
  i=$((i + 1)); [ "$i" -le 60 ] || { echo "PostgreSQL temporário não subiu" >&2; exit 1; }
  sleep 2
done
docker exec -i "$NAME" pg_restore -U postgres -d verificacao --no-owner --exit-on-error < "$DUMP"

query() { docker exec "$NAME" psql -U postgres -d verificacao -tAc "$1"; }
TABLES="$(query "select count(*) from information_schema.tables where table_schema = 'public'")"
REVISION="$(query "select version_num from alembic_version")"
USERS="$(query "select count(*) from users")"
MEDIA="$(query "select count(*) from media")"
echo "[verify] $TABLES tabelas, migração $REVISION, $USERS usuários, $MEDIA mídias"
[ "$TABLES" -gt 0 ] && [ -n "$REVISION" ] && [ "$USERS" -gt 0 ] || {
  echo "a cópia restaurada não tem os dados esperados" >&2; exit 1; }
echo "[verify] cópia restaurável"
