# Repository Guidelines (Level 7.0 Precursor - Sovereign Knowledge Base)

## Project Structure & Module Organization
Backend code lives in `src/`, grouped by bounded contexts such as `media_management`, `media_processing`, `text_analysis`, `storage`, and `admin`. The system operates as a **Modular Monolith** with **Clean Architecture** and **DDD**.

- `media_processing`: Orchestrates the Multimodal pipeline (Whisper for audio, Moondream 2 for vision). Celery tasks are in the module-root `tasks.py`.
- `text_analysis`: Granular pipeline (Chunking -> Sentiment -> Topics -> Visual Integration -> Summary). Uses Llama 3 for synthesis.
- `storage`: High-level ports for swappable backends (Local/S3/MinIO). Includes `StorageMaintenanceService` for cleanup.
- `shared`: Common domain events, infrastructure middleware, and the `pgvector` semantic indexing bridge.

### Core Architectural Mandates
- **Pure Dependency Injection**: All dependencies MUST be composed in `main.py` via `bootstrap.py` factories. Avoid global singletons.
- **Hexagonal Integrity**: Business logic interacts with the world only through Ports (`application/ports.py`). Adapters stay in `infrastructure/`.
- **Granular Pipeline**: Analysis is step-based. Partial results MUST be saved to allow resilience and adaptive retries.
- **Semantic indexing**: Every processed chunk is vectorized via `pgvector` for global semantic search.

### Module Deprecations & Cleanup Status
- `media_management`: `MediaService` is the unique orchestrator. Legacy `MediaOrchestrator` and utilities are removed.
- `monitoring`: Partially legacy. Prefer using the new observability ports (`LoggerPort`, `MetricsPort`).
- `tests`: Directories like `tests/unit/auth` are removed. Unit tests reside within context folders (e.g., `tests/unit/user_management`).

## Intelligence & Autonomy Features
- **Multimodal Vision**: Uses Moondream 2 to describe keyframes. Agent should ensure the `VisualAnalysisPort` is used for visual context.
- **Human-in-the-loop (HITL)**: Supports rating and editing AI outputs. Updates to summaries must preserve versioning for future fine-tuning.
- **Hardware Awareness**: `HardwareAdvisor` monitors GPU/RAM pressure. Pipelines should be "adaptive" (e.g., smaller chunks if VRAM is low).
- **JSONB Upcasting**: Persistence uses JSONB for metadata to support zero-downtime schema evolution.

## Build, Test, and Development Commands
- **Backend**: `poetry run uvicorn main:app --reload` or `docker-compose up`.
- **Migrations**: `docker-compose exec backend alembic upgrade head`.
- **Tests**: `poetry run pytest` (Unit, Integration, E2E). 90+ tests must pass.
- **Linting**: `poetry run ruff check --fix` and `poetry run mypy .`.
- **Architecture**: `lint-imports` checks the layer and module rules in `.importlinter` (also in CI). Composition code (`bootstrap.py`, `tasks.py`, `worker*.py`) lives at the module root, never in `application/`.

## Coding Style & Naming Conventions
- **Python**: 4-space indent, Ruff formatting, strict type hints.
- **Layering**: Stick to `Domain` -> `Application` -> `Infrastructure`.
- **TypeScript**: React 18 with TanStack Query. Use PascalCase for components.

## Testing Guidelines
- Unit tests MUST use mocks for all external dependencies (Repositories, EventBus).
- Integration tests verify Port/Adapter connectivity.
- E2E tests (`tests/e2e`) validate the entire Multimodal flow from upload to summary correction.

## Commit & Pull Request Guidelines
- **Conventional Commits**: `feat(vision): ...`, `fix(vector): ...`.
- **PRs**: Must include validation logs and confirm that architectural purity (DI/Hexagonal) is maintained.
