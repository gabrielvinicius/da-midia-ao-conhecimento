# Media Processing API & Real-Time Frontend

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue.svg)](https://www.typescriptlang.org/)
[![WebSockets](https://img.shields.io/badge/WebSockets-✓-green.svg)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

An advanced, asynchronous API and a feature-rich, real-time frontend for uploading, processing, and analyzing media files. The project is built with a focus on a clean, event-driven, and modular architecture for high scalability, maintainability, and resilience.

This project serves as a comprehensive, real-world example of applying modern, end-to-end software architecture patterns.

## Key Features

- **Event-Driven Media Pipeline**: Upload videos, audio files, or text, and the system automatically routes them through the correct, non-blocking processing pipeline.
- **Interactive Transcription with Timestamps**: Play media files while the corresponding text segments are highlighted in real-time. Click on any text segment to jump to that precise moment in the audio/video.
- **Real-Time UI (Observer Pattern)**: Receive instant updates on media processing status via WebSockets. The backend (`Subject`) actively pushes notifications and status changes to the frontend (`Observer`) for a fully reactive user experience.
- **Feature-Rich Admin Panel**: A secure, dedicated administrative area to manage users and media, view system statistics, and reprocess failed jobs.
- **Highly-Architected Frontend**: A fully-refactored, responsive interface built with TypeScript, React, and Vite. Its architecture is feature-based, modular, and highly scalable, featuring a custom design system built on **Shadcn/ui** and **TailwindCSS**.
- **Dynamic Provider Selection**: Choose at runtime which service provider to use for storage, transcription, and summarization.

## Architectural Deep Dive

For a detailed overview of how the backend composes modules, shared resources, and cross-context integrations, read the updated [architecture guide](docs/architecture.md).

This project is a practical implementation of several advanced software architecture patterns:

- **Modular Monolith & Domain-Driven Design (DDD)**: The application is organized into Bounded Contexts (e.g., `media_management`, `transcription`, `notifications`), each with its own clear domain.
- **Event-Driven Architecture**: The core business logic is an event-driven pipeline. For example, a `MediaUploaded` event triggers `video_processing`, which produces an `AudioExtracted` event, which then triggers `transcription`.
- **Observer Pattern & Real-Time Communication**: The system uses WebSockets to implement the Observer pattern, allowing the backend to push state changes to the frontend in real-time without polling.
- **CQRS (Command Query Responsibility Segregation)**: Each module separates its write operations (Commands) from its read operations (Queries).
- **Clean Frontend Architecture**: The frontend is organized by features, not types. Each feature encapsulates its own API calls, state management hooks (with React Query), and UI components, promoting high cohesion and low coupling.

## Tech Stack

- **Backend**: FastAPI, Python 3.11, WebSockets, Gunicorn, Uvicorn
- **Frontend**: React, TypeScript, Vite, React Query, TailwindCSS, Shadcn/ui, React Hook Form, Zod
- **Data Persistence**: PostgreSQL (with SQLAlchemy & Alembic)
- **Asynchronous Tasks & Messaging**: Celery, Redis
- **Object Storage**: MinIO (S3-compatible), Local File System
- **Observability**: OpenTelemetry, Jaeger, Prometheus
- **Containerization**: Docker, Docker Compose

## Getting Started

### 1. Prerequisites

- Docker & Docker Compose
- Node.js & npm (v18+ recommended)

### 2. Environment Setup

Copy the example environment file for the backend. The default values are configured to work with the local Docker Compose setup.

```bash
cp .env.example .env
```

### 3. Run for Local Development

#### Backend

This command starts the entire backend infrastructure (API, database, Redis, etc.).

```bash
docker-compose up --build
```

- **API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`

#### Frontend

In a separate terminal, navigate to the `frontend` directory, install dependencies, and start the development server.

```bash
cd frontend
npm install
npm run dev
```

- **Frontend App**: `http://localhost:5173` (or the port specified by Vite)

### 4. Apply Database Migrations

After starting the containers for the first time, open a new terminal and run the Alembic migrations to set up the database schema.

```bash
docker-compose exec backend alembic upgrade head
```

## Core API Overview

- **`POST /media/`**: Upload a new media file to start the processing pipeline.
- **`GET /media/{media_id}/stream`**: Streams the content of a media file for playback.
- **`GET /transcriptions/?media_id={media_id}`**: Retrieve the final transcription with timestamped segments.
- **`POST /auth/token`**: Log in to get a JWT access token.
- **`PUT /auth/me/password`**: Allows an authenticated user to change their password.
- **`GET /admin/users`**: (Admin) Retrieves a paginated list of all users.
- **`PUT /admin/users/{user_id}`**: (Admin) Updates a user's role.
- **`DELETE /admin/users/{user_id}`**: (Admin) Deletes a user.
- **`POST /admin/media/{media_id}/reprocess`**: (Admin) Re-triggers the processing for a failed media item.
- **`GET /notifications/ws`**: Establishes a WebSocket connection for real-time notifications and status updates.

## End-to-End Testing

This project includes a comprehensive suite of end-to-end (E2E) tests using Playwright to ensure the frontend functionality works as expected.

### Running E2E Tests

To run the E2E tests:

```bash
# Execute all E2E tests
cd frontend
npx playwright test

# Run tests in headed mode (visible browsers)
npx playwright test --headed

# Run tests in debug mode with inspector
npx playwright test --debug

# Run a specific test file
npx playwright test tests/e2e/auth/login.spec.ts
```

For more information about the E2E tests, check the [E2E_TESTS.md](frontend/E2E_TESTS.md) file in the frontend directory.
