# syntax=docker/dockerfile:1
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE} AS base

# Configurações globais
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalação de dependências de sistema comuns
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libfontconfig1 \
    libxrender1 \
    libgomp1 \
    tesseract-ocr \
    tesseract-ocr-por \
    curl \
    git \
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

# --- Stage de Build ---
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential pkg-config libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Índice do PyTorch: cu124 (GPU NVIDIA, padrão), cpu ou rocm6.2 (GPU AMD).
# O torch é instalado primeiro, a partir desse índice; o restante das
# dependências o reaproveita em vez de baixar outra variante.
ARG PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cu124

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    TORCH_PIN="$(grep -E '^torch==' requirements.txt)" && \
    pip install --user --no-warn-script-location \
    --index-url ${PYTORCH_INDEX_URL} "${TORCH_PIN}" && \
    grep -vE '^torch==' requirements.txt > /tmp/requirements-sem-torch.txt && \
    pip install --user --no-warn-script-location -r /tmp/requirements-sem-torch.txt

# --- Stage Final ---
FROM base AS runtime

LABEL org.opencontainers.image.title="Video Summarizer API" \
      org.opencontainers.image.description="Enterprise Autonomous Media Intelligence" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.authors="Gemini Level 6.0 Agent"

# Criar usuário não-root
RUN groupadd -r appuser && useradd -m -r -g appuser appuser

# Copiar dependências do builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copiar código e configurar permissões
COPY --chown=appuser:appuser . .
RUN chmod +x /app/docker/*.sh

# Persistência e Cache
RUN mkdir -p /app/logs /app/media /app/storage /app/data /app/.cache && \
    chown -R appuser:appuser /app /home/appuser

USER appuser



EXPOSE 8000

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/app/docker/backend-entrypoint.sh"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


