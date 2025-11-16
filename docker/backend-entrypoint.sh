#!/bin/sh
set -e

MAX_RETRIES=${ALEMBIC_MAX_RETRIES:-10}
SLEEP_SECONDS=${ALEMBIC_RETRY_DELAY:-5}
COUNT=1
MIGRATION_GENERATED=0

echo "[entrypoint] waiting for database, generating migrations and running upgrades..."
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
