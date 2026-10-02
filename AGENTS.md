# Repository Guidelines

## Project Structure & Module Organization
Backend code lives in `src/`, grouped by bounded contexts such as `media_management`, `media_processing`, `text_analysis`, `storage`, and `admin`. The system operates as a **Modular Monolith** with **Clean Architecture** and **DDD**.

- `media_processing`: Orchestrates the Multimodal pipeline (Whisper for audio, Moondream 2 for vision). Celery tasks are in the module-root `tasks.py`.
- `text_analysis`: Granular pipeline (Chunking -> Sentiment -> Topics -> Indexing -> Topic titles -> Summary -> Grounding check). Synthesis via Ollama (Qwen3.5-9B, Gemma 4 as reserve). Frame descriptions arrive ready from `media_processing`.
- `storage`: High-level ports for swappable backends (Local/S3/MinIO). Includes `StorageMaintenanceService` for cleanup.
- `shared`: Common domain events, infrastructure middleware, and the `pgvector` semantic indexing bridge.

### Core Architectural Mandates
- **Pure Dependency Injection**: All dependencies MUST be composed in `main.py` via `bootstrap.py` factories. Avoid global singletons. The only process-wide state allowed is explicit and centralized: loaded AI models in `shared/infrastructure/model_cache.py` and the worker's event bus in `shared/infrastructure/messaging/process_bus.py`.
- **Shared kernel**: application and domain code may import only `shared.domain` and `shared.application` (ports such as `LoggerPort`, `SupportsEventBus`, `UnitOfWorkPort`, `UserRole`), never `shared.infrastructure`.
- **Data ownership**: a module queries only its own tables (enforced by `tests/unit/test_architecture_table_ownership.py`); to know about another module's data, define a port and let that module implement it.
- **Integration events**: each event in `shared/domain/events.py` declares `published_by`; only that module creates it (`tests/unit/test_architecture_event_ownership.py`).
- **Event payloads**: events carry typed fields only, never a free `metadata` dict (checked by the same test). IDs travel as strings and become UUIDs on entry through `shared/domain/value_objects/identifiers.py` (`parse_id`, `parse_media_id`).
- **Queues**: Celery task and queue names live in `shared/events/integration_events.py`; the `-Q` lists in the docker-compose files must match (`tests/unit/test_queue_names.py`).
- **Transactions**: a repository commits its own single-aggregate change; a use case that touches several repositories runs inside `UnitOfWorkPort.transaction()` (repositories then only flush).
- **Single composition**: each application service has one factory, in its module's `infrastructure/dependencies/builders.py`, used by the API bootstrap, the workers and the event handlers alike. API dependency defaults (`api/dependencies.py`) never build services; they raise until `bootstrap.bind_*_module` binds the instance (`tests/unit/test_architecture_single_composition.py`).
- **Errors**: application and domain errors extend `shared/domain/errors.py` (`NotFoundError`, `AccessDeniedError`, `ConflictError`, `TemporarilyUnavailableError`, `ValidationError`, `DomainError`). They are translated to HTTP in one place (`shared/infrastructure/exceptions/exception_handlers.py`); routes don't catch them just to change the status code. Unexpected errors become a 500 without the internal message.
- **Complexity**: functions stay at McCabe complexity 12 or less (checked in CI); split long flows into named steps.
- **Data model**: ids are UUID; timestamps are `DateTime(timezone=True)` in UTC (`shared/domain/time/clock.utcnow`); enums are stored as text via `shared/infrastructure/database/types.enum_column` (no native PostgreSQL enums). Tables derived from a media reference `media.id` with a foreign key; deletion is done by the application (`MediaDataEraserPort` per media, `UserDataEraserPort` per user), never by cascades across modules.
- **Repositories**: map rows to domain objects right away; no `rollback` before reads (a failed commit is rolled back inside `unit_of_work.commit`); no `refresh` after commit unless a server-side default must be read.
- **Rich entities**: state changes go through entity methods (`mark_as_failed`, `override_status`, `mark_as_extracted`), never by assigning `status` from services.
- **Observability**: logs are JSON by default (`LOG_FORMAT=console` for local reading) and every line carries the `correlation_id` bound in `contextvars` by `CorrelationIdMiddleware` (API) or `task_prerun` (Celery). The request id travels in `MediaUploaded` to the queued tasks. Prometheus metrics are never served by the public API: API and workers expose them on the internal `METRICS_PORT` (workers in multiprocess mode, `PROMETHEUS_MULTIPROC_DIR`), scraped by the `prometheus` Compose service. `/health` checks the database and Redis and answers 503 when one is down.
- **Analysis factors**: sentiment, topics (with titles) and grounding are optional (`ANALYSIS_FACTORS`); frame description is switched off with `VISUAL_PROVIDER=none`. A switched-off factor is left out of the pipeline and its model is never loaded; later steps must cope with its absence. Chunking, chunk embeddings, indexing and synthesis always run.
- **Text generation**: only through Ollama (`OllamaTextGenerationAdapter`, main and reserve model from settings). There is no Transformers path for the LLM.
- **Configuration**: environment-specific values (CORS origins in `CORS_ORIGINS`, hosts, models) come from settings, never hard-coded lists.
- **Hexagonal Integrity**: Business logic interacts with the world only through Ports (`application/ports.py`). Adapters stay in `infrastructure/`.
- **Granular Pipeline**: Analysis is step-based. Partial results MUST be saved to allow resilience and adaptive retries.
- **Semantic indexing**: Every processed chunk is vectorized via `pgvector` for global semantic search.

### Module Deprecations & Cleanup Status
- `media_management`: each operation is a use-case class in `application/use_cases/` (`UploadMedia`, `DeleteMedia`, `ReprocessMedia`, `StreamMedia`, `MediaLifecycle`); `MediaService` is only a facade over them.
- `monitoring`: only `HardwareAdvisor` and `gpu_stats` (admin panel). Logging and metrics live in `shared/infrastructure/observability`.
- `tests`: Directories like `tests/unit/auth` are removed. Unit tests reside within context folders (e.g., `tests/unit/user_management`).

## Intelligence & Autonomy Features
- **Multimodal Vision**: Moondream 2 describes keyframes in `media_processing`, right after transcription, through `VisualAnalysisPort`.
- **Human-in-the-loop (HITL)**: Supports rating and editing AI outputs. Updates to summaries must preserve versioning for future fine-tuning.
- **Hardware Awareness**: `HardwareAdvisor` reports GPU/RAM pressure (whole-GPU readings via `nvidia-smi`) for the admin panel and processing deadlines.
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
