# Video Summarizer: Global Knowledge Base (Level 7.0 Precursor)

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue.svg)](https://www.typescriptlang.org/)
[![pgvector](https://img.shields.io/badge/pgvector-✓-blue.svg)](https://github.com/pgvector/pgvector)

**Video Summarizer** has evolved from a simple media processor into a **Sovereign Knowledge Base**. Operating at **Level 7.0 Precursor**, the system combines computer vision, speech recognition, and advanced NLP to transform raw media into a searchable, interactive, and self-improving intelligence asset.

## 💎 Level 7.0 Key Features

- **Multimodal Video Intelligence**: The system doesn't just listen; it **sees**. Using **Moondream 2**, it extracts visual insights from video frames (e.g., describing charts, actions, or scenes) to enrich textual summaries.
- **Global Semantic Search (Vector DB)**: Powered by **pgvector**, you can query your entire media library using natural language. Find "where we discussed server costs" across hundreds of videos instantly based on meaning, not just keywords.
- **Human-in-the-loop Feedback**: A complete cycle of continuous learning. Users can evaluate AI outputs (👍/👎) and manually correct summaries. These corrections are versioned, creating a high-quality dataset for future fine-tuning.
- **Full Text & Document Support**: Native extraction and OCR for PDF, DOCX, and images (PNG/JPG). Scanned documents are automatically routed to the OCR pipeline (Tesseract).
- **Self-Healing & Predictive UI**: Real-time hardware pressure monitoring and automated recovery from AI failures (adaptive chunking).

## 🏗️ Architectural Excellence

- **Pure Dependency Injection**: Dependencies are composed at the root (`main.py`) for absolute testability.
- **Hexagonal Architecture**: Strict Port/Adapter separation ensures infrastructure (Postgres, S3, Llama 3) remains swappable.
- **Granular Pipeline**: Analysis is broken into independent, resilient steps (Chunking -> Sentiment -> Topics -> Visual -> Summary).

## 🚀 Tech Stack

- **Backend**: FastAPI, Celery, Redis, SQLAlchemy, pgvector.
- **Frontend**: React 18, TanStack Query, TailwindCSS, Shadcn/UI.
- **AI/ML**: Meta Llama 3 (8B), Moondream 2 (Vision), OpenAI Whisper, BERTopic.
- **Infrastructure**: Docker (NVIDIA CUDA 13.0 / AMD ROCm 6.2), MinIO.

## 🧪 Quality Assurance

- **90+ Tests Passing**: Unit, Smoke, Integration, and Intelligence validation.
- **Gold Standard (100%)**: Architectural purity across all modules.

---
Transforming media noise into structured organizational intelligence. 🚀💎


