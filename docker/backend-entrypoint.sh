#!/bin/sh
set -e

MAX_RETRIES=${ALEMBIC_MAX_RETRIES:-10}
SLEEP_SECONDS=${ALEMBIC_RETRY_DELAY:-5}
COUNT=1

# HF_TOKEN (opcional) é lido direto pela biblioteca da Hugging Face. Antes,
# o "hf auth login" com credential.helper store gravava o token em texto puro
# dentro do contêiner.

echo "[entrypoint] waiting for the database and applying migrations (alembic upgrade head)..."
while [ "$COUNT" -le "$MAX_RETRIES" ]; do
  if alembic upgrade head; then
    echo "[entrypoint] migrations applied"
    break
  fi

  echo "[entrypoint] alembic failed (attempt $COUNT/$MAX_RETRIES), retrying in $SLEEP_SECONDS seconds..."
  COUNT=$((COUNT + 1))
  sleep "$SLEEP_SECONDS"
done

if [ "$COUNT" -gt "$MAX_RETRIES" ]; then
  echo "[entrypoint] failed to run migrations after $MAX_RETRIES attempts"
  exit 1
fi

exec "$@"
