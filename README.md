# Video Summarizer API

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-20.10-blue.svg)](https://www.docker.com/)

An asynchronous API for uploading, transcribing, and summarizing videos, built with a focus on modern software architecture patterns for scalability, maintainability, and resilience.

## Key Features

- **Asynchronous Processing**: Upload videos and receive transcriptions and summaries via a non-blocking, event-driven workflow using Celery and Redis.
- **Dynamic Provider Selection**: Choose at runtime which service provider to use for storage (`local`, `s3`), transcription (`whisper`, `fastwhisper`), and summarization (`huggingface`).
- **Full Observability**: Integrated with the three pillars of observability:
  - **Logging**: Structured logging with `structlog`.
  - **Metrics**: Application and business metrics exposed in Prometheus format at `/metrics`.
  - **Tracing**: End-to-end distributed tracing with OpenTelemetry and Jaeger.
- **Resilient by Design**: Implements the Circuit Breaker pattern to protect against failures in external services.
- **Clean, Modular Architecture**: Built on a foundation of professional software design patterns.

## Architectural Overview

This project is a practical implementation of several advanced software architecture patterns, designed to create a robust and scalable system.

- **Modular Monolith & Domain-Driven Design (DDD)**: The application is organized into Bounded Contexts (e.g., `auth`, `video_management`, `transcription`), each with its own clear domain and boundaries.

- **CQRS (Command Query Responsibility Segregation)**: Each module separates its write operations (Commands) from its read operations (Queries). This simplifies the logic, allows for independent optimization, and improves maintainability.

- **Plugin-Based Provider System**: The system uses a factory and registration pattern, allowing new providers for storage, transcription, or summarization to be added dynamically just by creating a new class. The API allows clients to discover and select these providers at runtime.

- **State Pattern**: The `Video` entity's lifecycle (`UPLOADED` -> `PROCESSING` -> `COMPLETED`/`FAILED`) is managed by a formal State Machine, ensuring that only valid state transitions can occur and encapsulating state-specific logic.

- **Explicit Composition Root**: The application's dependency injection is decentralized. Each module bootstraps its own services, and the `main.py` file acts as the final "Composition Root," explicitly composing the application and its cross-context dependencies.

## Tech Stack

- **Backend**: FastAPI, Python 3.11
- **Data Persistence**: PostgreSQL (with SQLAlchemy)
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

## Running Tests

To run the unit tests, execute the following command from the root of the project:

```bash
pytest
```

## API Overview

- **`GET /providers/{type}`**: Discover available providers for `storage`, `transcription`, or `summarization`.
- **`POST /auth/register`**: Create a new user.
- **`POST /auth/token`**: Log in to get a JWT access token.
- **`POST /videos/`**: Upload a video. You can specify the storage provider with the `?storage_provider=s3` query parameter.
- **`POST /videos/{video_id}/transcription`**: Request a transcription for an existing video. You can specify the provider with `?provider=fastwhisper`.
- **`POST /summaries/`**: Request a summary for an existing transcription. You can specify the provider with `?provider=huggingface`.
