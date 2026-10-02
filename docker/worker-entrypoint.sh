#!/bin/sh
set -e

echo "[entrypoint] Checking Hugging Face authentication..."
if [ -n "$HF_TOKEN" ]; then
  echo "[entrypoint] HF_TOKEN found, logging in..."
  git config --global credential.helper store
  hf auth login --token "$HF_TOKEN" --add-to-git-credential
else
  echo "[entrypoint] HF_TOKEN not set, skipping login."
fi

# Métricas dos processos filhos do Celery (prometheus_client multiprocesso):
# a pasta começa vazia a cada partida do worker.
if [ -n "$PROMETHEUS_MULTIPROC_DIR" ]; then
  rm -rf "$PROMETHEUS_MULTIPROC_DIR"
  mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
fi

echo "[entrypoint] Starting worker process..."
exec "$@"
