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
# Sem os envios em partes ainda em andamento (MEDIA_MEDIA_UPLOAD_STAGING_DIR).
restic -v "$MEDIA_SOURCE:/dados/midias:ro" "$RESTIC_IMAGE" backup /dados/midias --tag midias \
  --exclude=/dados/midias/.envios-em-partes

if [ -n "$S3_SOURCE" ]; then
  echo "[backup] S3 local, Garage ($S3_SOURCE)"
  # Os blocos de dados não mudam depois de gravados; o banco de metadados em
  # uso pode estar no meio de uma escrita. Com o Garage no ar, vai a cópia
  # que ele mesmo tira (meta/snapshots) e o banco em uso fica de fora.
  EXCLUDE=""
  if garage_running; then
    docker compose exec -T garage /garage meta snapshot >/dev/null
    EXCLUDE="--exclude=/dados/s3/meta/db.sqlite*"
  fi
  # shellcheck disable=SC2086 # EXCLUDE é vazio ou uma opção só.
  restic -v "$S3_SOURCE:/dados/s3:ro" "$RESTIC_IMAGE" backup /dados/s3 --tag s3 $EXCLUDE
fi

echo "[backup] retenção e verificação"
restic "$RESTIC_IMAGE" forget --prune --group-by tags \
  --keep-daily "$(env_value BACKUP_KEEP_DAILY | grep . || echo 14)" \
  --keep-weekly "$(env_value BACKUP_KEEP_WEEKLY | grep . || echo 8)" \
  --keep-monthly "$(env_value BACKUP_KEEP_MONTHLY | grep . || echo 12)"
restic "$RESTIC_IMAGE" check

echo "[backup] pronto"
restic "$RESTIC_IMAGE" snapshots --latest 1 --group-by tags
