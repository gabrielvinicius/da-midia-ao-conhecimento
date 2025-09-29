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
  - **Tracing**: End-to-end distributed tracing with OpenTelemetry and Jaeger to visualize the entire request lifecycle, from API call to final processing.
- **Resilient by Design**: Implements the Circuit Breaker pattern to protect against failures in external AI/ML services.

## Architectural Deep Dive

This project is a practical implementation of several advanced software architecture patterns:

- **Modular Monolith & Domain-Driven Design (DDD)**: The application is organized into Bounded Contexts (e.g., `media_management`, `video_processing`, `transcription`), each with its own clear domain and boundaries.

- **Event-Driven Pipeline**: The core business logic is an event-driven pipeline. For example, a `MediaUploaded` event can trigger the `video_processing` module, which in turn produces an `AudioExtracted` event, which then triggers the `transcription` module, and so on. This makes the system highly extensible and decoupled.

- **CQRS (Command Query Responsibility Segregation)**: Each module separates its write operations (Commands and Handlers) from its read operations (Queries). This simplifies the logic, allows for independent optimization, and improves maintainability.

- **State Pattern**: The `Media` entity's lifecycle (`UPLOADED` -> `PROCESSING` -> `COMPLETED`/`FAILED`) is managed by a formal State Machine, ensuring that only valid state transitions can occur and encapsulating state-specific logic.

- **Explicit Composition Root**: The application's dependency injection is fully decentralized. Each module bootstraps its own services in a dedicated `bootstrap.py` file. The `main.py` file acts as the final "Composition Root," explicitly composing the application and its cross-context dependencies.

## Tech Stack

- **Backend**: FastAPI, Python 3.11
- **Data Persistence**: PostgreSQL (with SQLAlchemy & Alembic)
- **Asynchronous Tasks & Messaging**: Celery, Redis
- **Object Storage**: MinIO (S3-compatible), Local File System
- **Observability**: OpenTelemetry, Jaeger, Prometheus
- **Containerization**: Docker, Docker Compose

## Getting Started (Local Development)

### Prerequisites

- Docker
- Docker Compose

### 1. Clone the Repository

```bash
git clone <repository-url>
cd video-summarizer
```

### 2. Create the Environment File

Copy the example environment file to create your local configuration.

```bash
cp .env.example .env
```

By default, the `.env` file is configured to use `localhost` for all services, which works seamlessly with Docker Compose. You do not need to change anything to get started.

### 3. Run the Application

Use Docker Compose to build and run all the services (API, Celery worker, Postgres, Redis, MinIO, and Jaeger).

```bash
docker-compose up --build
```

- **API**: Available at `http://localhost:8000`
- **API Docs (Swagger)**: Available at `http://localhost:8000/docs`
- **MinIO Console (S3)**: Available at `http://localhost:9001`
- **Jaeger UI (Tracing)**: Available at `http://localhost:16686`

### 4. Apply Database Migrations

After starting the containers for the first time, open a new terminal and run the Alembic migrations to set up the database schema.

```bash
alembic upgrade head
```

## Running Tests

To run the unit tests, execute the following command from the root of the project:

```bash
pytest
```

## API Overview

- **`GET /providers/{type}`**: Discover available providers for `storage`, `transcription`, or `summarization`.
- **`POST /auth/token`**: Log in to get a JWT access token.
- **`POST /media/`**: Upload a new media file (video, audio, PDF, etc.). This is the main entry point for the processing pipeline. You can specify the storage provider with the `?storage_provider=s3` query parameter.
- **`POST /videos/{video_id}/transcription`**: (Legacy-style, can be used to re-trigger) Request a transcription for an existing media item. You can specify the provider with `?provider=fastwhisper`.
- **`GET /summaries/{summary_id}`**: Retrieve a completed summary.
