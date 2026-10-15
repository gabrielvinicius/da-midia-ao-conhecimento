#!/bin/sh
# Cópia de segurança do banco e das mídias enviadas, num repositório restic
# (incremental, com deduplicação e criptografia).
# Uso, na pasta do projeto, com o postgres no ar:
#   sh scripts/ops/backup.sh
# Lê do .env: BACKUP_REPOSITORY (pasta do host ou outro destino do restic,
# como s3:...), BACKUP_PASSWORD (chave do repositório: sem ela, as cópias não
# podem ser lidas; guarde-a fora desta máquina) e, opcionalmente,
# BACKUP_KEEP_DAILY/WEEKLY/MONTHLY. O repositório é criado na primeira vez.
#
# Antes, cada execução gerava um tar.gz com todas as mídias (2,2 GB por cópia
# já em outubro de 2026, crescendo a cada envio), sem retenção nem
# verificação. Com o restic, só o que mudou é gravado, as cópias antigas saem
# pela política de retenção e a integridade do repositório é conferida ao
# final. Os modelos de IA não entram (são baixados de novo).
set -eu
. scripts/ops/restic-env.sh

restic "$RESTIC_IMAGE" cat config >/dev/null 2>&1 || {
  echo "[backup] criando o repositório em $REPOSITORY"
  restic "$RESTIC_IMAGE" init
}

echo "[backup] banco ${DB_NAME:-app}"
# Formato próprio do pg_dump (compactado, restauração seletiva). Primeiro em
# arquivo: num pipe, uma falha do pg_dump passava despercebida e virava uma
# cópia vazia.
DUMP="$(mktemp)"
trap 'rm -f "$DUMP"' EXIT
docker compose exec -T postgres pg_dump -U "${DB_USER:-postgres}" -d "${DB_NAME:-app}" -Fc > "$DUMP"
[ -s "$DUMP" ] || { echo "dump do banco vazio" >&2; exit 1; }
restic "$RESTIC_IMAGE" backup --stdin --stdin-filename banco.dump --tag banco < "$DUMP"

echo "[backup] mídias ($MEDIA_SOURCE)"
restic -v "$MEDIA_SOURCE:/dados/midias:ro" "$RESTIC_IMAGE" backup /dados/midias --tag midias

echo "[backup] retenção e verificação"
restic "$RESTIC_IMAGE" forget --prune --group-by tags \
  --keep-daily "$(env_value BACKUP_KEEP_DAILY | grep . || echo 14)" \
  --keep-weekly "$(env_value BACKUP_KEEP_WEEKLY | grep . || echo 8)" \
  --keep-monthly "$(env_value BACKUP_KEEP_MONTHLY | grep . || echo 12)"
restic "$RESTIC_IMAGE" check

echo "[backup] pronto"
restic "$RESTIC_IMAGE" snapshots --latest 1 --group-by tags
