# Multi-stage Dockerfile optimized for Video Summarizer
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Prefer CUDA-enabled wheels (host provides NVIDIA driver); see https://download.pytorch.org/whl/cu124
    PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cu124

# Stage 1: Builder
FROM base AS builder

WORKDIR /app

# Install system dependencies needed for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir --no-warn-script-location -r requirements.txt

# Stage 2: Runtime
FROM base AS runtime

WORKDIR /app

# Install only necessary runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libfontconfig1 \
    libxrender1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .
COPY --chown=appuser:appuser docker/backend-entrypoint.sh /app/backend-entrypoint.sh
RUN chmod +x /app/backend-entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/logs /app/media /app/storage /app/data /app/.cache/whisper /home/appuser/.cache && \
    chown -R appuser:appuser /app /home/appuser/.cache

# Add user's local directory to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENTRYPOINT ["/app/backend-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
