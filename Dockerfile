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
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

# --- Stage de Build ---
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential pkg-config libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Índice do PyTorch: cu126 (GPU NVIDIA, padrão), cpu ou rocm7.2 (GPU AMD).
# CUDA 12, e não 13: a transcrição (CTranslate2) carrega o libcublas.so.12.
# O torch é instalado primeiro, a partir desse índice; o restante das
# dependências o reaproveita (a versão fixada vai como restrição: sem ela, o
# pip o trocava por um torch mais novo do PyPI, de outra variante de CUDA).
ARG PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cu126

COPY requirements.txt .
# Só o pip é atualizado fora do --user: setuptools e wheel (que traz o
# packaging) instalados no sistema do builder "satisfaziam" essas dependências,
# o pip --user as pulava, e a imagem final, que copia só /root/.local, ficava
# sem elas (a API não subia: "No module named 'packaging'"). Pacotes compilados
# do código-fonte recebem o setuptools pelo isolamento de build.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    grep -E '^(torch|torchvision)==' requirements.txt > /tmp/torch-constraint.txt && \
    pip install --user --no-warn-script-location \
    --index-url ${PYTORCH_INDEX_URL} -r /tmp/torch-constraint.txt && \
    grep -vE '^(torch|torchvision)==' requirements.txt > /tmp/requirements-sem-torch.txt && \
    pip install --user --no-warn-script-location \
    -r /tmp/requirements-sem-torch.txt -c /tmp/torch-constraint.txt

# --- Stage Final ---
FROM base AS runtime

# Criar usuário não-root
RUN groupadd -r appuser && useradd -m -r -g appuser appuser

# Copiar dependências do builder, já com o dono certo. Antes, um "chown -R"
# depois de copiar o código percorria esses GB a cada mudança de código (~10
# min por imagem).
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH \
    XDG_CACHE_HOME=/app/.cache
# A transcrição (CTranslate2) carrega o cuBLAS e o cuDNN pelo nome. Eles vêm
# nos pacotes nvidia-* que o torch de CUDA instala, fora do caminho padrão:
# antes, só eram achados se algum módulo tivesse importado o torch antes da
# transcrição. Com a descrição dos quadros pelo Ollama, ninguém importava, e
# toda transcrição falhava ("libcublas.so.12 is not found"). Nas variantes CPU
# e ROCm as pastas não existem e a variável não tem efeito.
ENV LD_LIBRARY_PATH=/home/appuser/.local/lib/python3.12/site-packages/nvidia/cublas/lib:/home/appuser/.local/lib/python3.12/site-packages/nvidia/cudnn/lib
# Modelos baixados (Hugging Face, faster-whisper, torch) ficam em /app/.cache,
# o volume ai_models_cache. Antes iam para /home/appuser/.cache, fora do
# volume: cada recriação do contêiner baixava GBs de novo, e o sistema deixava
# de funcionar sem internet.

# Copiar código e configurar permissões
COPY --chown=appuser:appuser . .
RUN chmod +x /app/docker/*.sh

# Mídias (armazenamento local) e modelos baixados; ambos viram volumes no compose.
RUN mkdir -p /app/storage /app/.cache && \
    chown appuser:appuser /app /app/storage /app/.cache

USER appuser

EXPOSE 8000

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/app/docker/backend-entrypoint.sh"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Por último: um valor novo a cada commit não invalida o cache das camadas
# acima. Commit de origem (a implantação e a CI passam VCS_REF): diz de que versão
# do código veio uma imagem em execução.
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="Da Mídia ao Conhecimento" \
      org.opencontainers.image.description="API e workers: transcrição, resumo e busca semântica de aulas gravadas" \
      org.opencontainers.image.source="https://github.com/gabrielvinicius/da-midia-ao-conhecimento" \
      org.opencontainers.image.revision="${VCS_REF}"


