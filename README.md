# Media Processing API

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-20.10-blue.svg)](https://www.docker.com/)

An asynchronous API for uploading, processing, and analyzing media files (video, audio, and text), built with a focus on a clean, event-driven, and modular architecture for high scalability, maintainability, and resilience.

This project serves as a comprehensive example of applying modern software architecture patterns to a real-world problem.

## Key Features

- **Generic Media Pipeline**: Abstracted beyond just video. Upload videos, audio files, or even PDFs, and the system automatically routes them through the correct processing pipeline.
- **Asynchronous & Event-Driven**: All processing is non-blocking. Media uploads trigger events that are handled by a robust pipeline of Celery workers, ensuring the API remains fast and responsive.
- **Dynamic Provider Selection**: Choose at runtime which service provider to use for storage (`local`, `s3`), transcription (`whisper`, `fastwhisper`), and summarization (`huggingface`).
- **Full Observability**: Integrated with the three pillars of observability:
  - **Logging**: Structured logging with `structlog`.
  - **Metrics**: Application and business metrics exposed in Prometheus format at `/metrics`.
  - **Tracing**: End-to-end distributed tracing with OpenTelemetry and Jaeger to visualize the entire request lifecycle.
- **Resilient by Design**: Implements the Circuit Breaker pattern to protect against failures in external AI/ML services.

## Architectural Deep Dive

This project is a practical implementation of several advanced software architecture patterns:

- **Modular Monolith & Domain-Driven Design (DDD)**: The application is organized into Bounded Contexts (e.g., `media_management`, `video_processing`, `transcription`), each with its own clear domain and boundaries.
- **Event-Driven Pipeline**: The core business logic is an event-driven pipeline. For example, a `MediaUploaded` event can trigger the `video_processing` module, which in turn produces an `AudioExtracted` event, which then triggers the `transcription` module, and so on.
- **CQRS (Command Query Responsibility Segregation)**: Each module separates its write operations (Commands and Handlers) from its read operations (Queries).
- **State Pattern**: The `Media` entity's lifecycle (`UPLOADED` -> `PROCESSING` -> `COMPLETED`/`FAILED`) is managed by a formal State Machine.
- **Explicit Composition Root**: The application's dependency injection is fully decentralized. Each module bootstraps its own services, and the `main.py` file acts as the final "Composition Root," explicitly composing the application.

## Tech Stack

- **Backend**: FastAPI, Python 3.11, Gunicorn, Uvicorn
- **Data Persistence**: PostgreSQL (with SQLAlchemy & Alembic)
- **Asynchronous Tasks & Messaging**: Celery, Redis
- **Object Storage**: MinIO (S3-compatible), Local File System
- **Observability**: OpenTelemetry, Jaeger, Prometheus
- **Containerization**: Docker, Docker Compose

## Getting Started

### 1. Prerequisites

- Docker
- Docker Compose

### 2. Environment Setup

Copy the example environment file. The default values are configured to work with the local Docker Compose setup.

```bash
cp .env.example .env
```

### 3. Run for Local Development

This command starts the API with hot-reloading for development.

```bash
docker-compose up --build
```

- **API**: `http://localhost:8000`
- **API Docs (Swagger)**: `http://localhost:8000/docs`
- **MinIO Console (S3)**: `http://localhost:9001`
- **Jaeger UI (Tracing)**: `http://localhost:16686`

### 4. Run for Production

This command uses the `docker-compose.prod.yml` file, which runs the application with the production-optimized `Dockerfile.prod` and uses `gunicorn` for stability and performance.

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### 5. Apply Database Migrations

After starting the containers for the first time (for either dev or prod), open a new terminal and run the Alembic migrations to set up the database schema.

```bash
alembic upgrade head
```

## Running Tests

- **Unit Tests**: Run directly on your host machine.
  ```bash
  pytest tests/unit
  ```
- **End-to-End Tests**: Run using the dedicated test environment.
  ```bash
  docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
  ```

## Core API Overview

- **`POST /media/`**: The main entry point. Upload a new media file (video, audio, PDF) to start the processing pipeline. Use the `?storage_provider=s3` query parameter to choose the storage backend.
- **`GET /media/{media_id}`**: Check the processing status of a media item.
- **`GET /transcriptions/?media_id={media_id}`**: Retrieve the final transcription for a processed media item.
- **`GET /summaries/?media_id={media_id}`**: Retrieve the final summary for a processed media item.
- **`GET /providers/{type}`**: Discover available providers for `storage`, `transcription`, or `summarization`.
- **`POST /auth/token`**: Log in to get a JWT access token.
