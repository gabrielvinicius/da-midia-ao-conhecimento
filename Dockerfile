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
    curl \
    git \
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

# --- Stage de Build ---
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential pkg-config libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# ARG para definir qual versão do Torch instalar (cpu, cu124, rocm6.1, etc)
ARG PYTORCH_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --user --no-warn-script-location \
    --extra-index-url ${PYTORCH_EXTRA_INDEX_URL} \
    -r requirements.txt

# --- Stage Final ---
FROM base AS runtime

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


