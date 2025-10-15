# Multi-stage Dockerfile otimizado para Video Summarizer
FROM python:3.11-slim as base

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Stage 1: Builder
FROM base as builder

WORKDIR /app

# Instalar dependências do sistema necessárias para build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    pkg-config \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --user --no-warn-script-location -r requirements.txt

# Stage 2: Runtime
FROM base as runtime

WORKDIR /app

# Instalar apenas dependências runtime necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libfontconfig1 \
    libxrender1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copiar dependências Python do builder
COPY --from=builder /root/.local /home/appuser/.local

# Copiar código da aplicação
COPY --chown=appuser:appuser . .

# Criar diretórios necessários
RUN mkdir -p /app/logs /app/media /app/data && \
    chown -R appuser:appuser /app

# Adicionar o diretório local do usuário ao PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Mudar para usuário não-root
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Comando padrão
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
