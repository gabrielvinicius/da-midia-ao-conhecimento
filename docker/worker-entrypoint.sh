#!/bin/sh
set -e

# HF_TOKEN (opcional) é lido direto pela biblioteca da Hugging Face. Antes,
# o "hf auth login" com credential.helper store gravava o token em texto puro
# dentro do contêiner.

# Métricas dos processos filhos do Celery (prometheus_client multiprocesso):
# a pasta começa vazia a cada partida do worker.
if [ -n "$PROMETHEUS_MULTIPROC_DIR" ]; then
  rm -rf "$PROMETHEUS_MULTIPROC_DIR"
  mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
fi

echo "[entrypoint] Starting worker process..."
exec "$@"
