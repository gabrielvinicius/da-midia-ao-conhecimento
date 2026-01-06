# Video Summarizer: Autonomous Media Intelligence (Level 6.0)

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue.svg)](https://www.typescriptlang.org/)
[![CUDA 13.0](https://img.shields.io/badge/CUDA-13.0-76E1FE.svg)](https://developer.nvidia.com/cuda-toolkit)

**Video Summarizer** is an enterprise-grade, autonomous platform for media analysis. It utilizes a **Modular Monolith** architecture (Clean Architecture + DDD) to provide highly resilient, hardware-aware transcription and summarization.

The system has reached **Maturity Level 6.0 (Autonomous & Adaptive)**, meaning it doesn't just process data—it manages its own resources, predicts failures, and self-heals in real-time.

## 💎 Level 6.0 Key Features

- **Intelligent Orchestration (Hardware-Aware)**: The system monitors CPU/GPU load in real-time. It dynamically selects between high-fidelity models (Llama 3 8B) or optimized fallbacks based on system pressure to prevent crashes.
- **Predictive UI & Observability**: Users receive instant feedback on processing costs, estimated time, and hardware risk *before* a task starts. A "Processing Trace" allows users to audit exactly which hardware and strategy was used.
- **Self-Healing Pipeline**: If an AI model fails due to memory limits or context overflow, the system automatically adapts (e.g., halves chunk sizes) and retries the operation without human intervention.
- **Zero-Downtime Schema Evolution**: Uses a "Schema-on-Read" pattern with JSONB upcasters, allowing the database structure to evolve without locking tables or requiring service downtime.
- **Interactive Sychronized Transcription**: A high-performance media player linked to timestamped text segments with automatic scrolling and "seek-on-click" capability.
- **Real-Time Reactive Updates**: Full integration with WebSockets and Redis Pub/Sub, ensuring the UI stays synchronized with backend workers even after network reconnections.

## 🏗️ Architectural Excellence

- **Pure Dependency Injection**: Every module is strictly decoupled. Dependencies are composed at the root (`main.py`) and injected via `bootstrap.py` factories.
- **Hexagonal Architecture (Ports & Adapters)**: Business logic is completely isolated from infrastructure (DB, S3, AI frameworks). Communication between modules happens through strict, typed interfaces.
- **Event-Driven Workflow**: High-performance asynchronous processing using Celery and Redis, with an in-process Event Bus for reactive module communication.
- **Modular Monolith**: Strict Bounded Contexts ensure that `media_management`, `text_analysis`, `auth`, and `notifications` can evolve independently or be extracted into microservices with minimal effort.

## 🚀 Tech Stack

- **Backend**: FastAPI, Python 3.12, Celery, Redis, SQLAlchemy (Async), Alembic.
- **Frontend**: React 18, TypeScript, Vite, TanStack Query (React Query), TailwindCSS, Shadcn/UI.
- **AI/ML**: Meta Llama 3 (8B), OpenAI Whisper, Faster-Whisper, BERTopic, Sentence-Transformers.
- **Infrastructure**: Docker, NVIDIA CUDA 13.0 / AMD ROCm 6.2, MinIO (S3), OpenTelemetry.

## 🛠️ Getting Started

### 1. Prerequisites
- Docker & Docker Compose
- NVIDIA Container Toolkit (for GPU support)
- Hugging Face Access Token (for Llama 3)

### 2. Run the Platform (NVIDIA GPU Recommended)
```bash
# Start with CUDA support (Level 6.0 Optimized)
docker compose -f docker-compose.yml -f docker-compose.cuda.yml up -d --build
```

### 3. Documentation
- [Architecture Deep Dive](docs/architecture.md)
- [Zero-Downtime Migration Policy](docs/internal/migration_policy.md)
- [API Documentation](http://localhost:8000/docs)

## 🧪 Quality Assurance

The system maintains a **Gold Standard (100%)** maturity level across all modules. 
- **Unit Tests**: Logic and Domain validation (`pytest tests/unit`).
- **Intelligence Tests**: Validating HardwareAdvisor and ResourcePredictor (`pytest tests/unit/shared/test_intelligence.py`).
- **E2E Tests**: Full flow validation with Playwright (`cd frontend && npx playwright test`).

---
Developed with a focus on absolute technical excellence and operational autonomy. 🚀💎

