#!/bin/sh
# Restaura uma cópia feita por backup.sh: substitui o banco e as mídias atuais.
# Uso, na pasta do projeto, com o postgres no ar:
#   sh scripts/ops/restore.sh            (a cópia mais recente)
#   sh scripts/ops/restore.sh <snapshot> (ids em: restic snapshots)
# O banco volta pelo pg_restore; as mídias, pelo restic (arquivos que não
# estavam na cópia são apagados). Os workers ficam parados durante a operação.
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
restic -v "$MEDIA_SOURCE:/dados/midias" "$RESTIC_IMAGE" restore "$SNAPSHOT" --tag midias \
  --target / --overwrite always --delete

echo "[restore] pronto"
