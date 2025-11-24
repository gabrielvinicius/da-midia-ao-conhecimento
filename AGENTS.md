# Repository Guidelines

## Project Structure & Module Organization
Backend code lives in `src/`, grouped by bounded contexts such as `media_management`, `media_processing`, `text_analysis`, and `admin` (the orchestration facade). Shared helpers stay in `src/shared`, background jobs in each module’s `tasks.py`, and FastAPI boots from `main.py`. Database migrations reside in `alembic/`, while operational scripts live in `scripts/`. Automated suites sit in `tests/` (`unit`, `integration`, `e2e`, `smoke`). The React frontend remains in `frontend/` with feature folders inside `frontend/src`. Architecture notes sit in `docs/`.

## Build, Test, and Development Commands
Spin up dependencies via `python -m venv .venv && source .venv/bin/activate` or rely on Poetry with `poetry install`. Launch the API through `poetry run uvicorn main:app --reload`; for full stack services use `docker-compose up --build`. Apply migrations with `docker-compose exec backend alembic upgrade head`. Frontend cycle: `cd frontend && npm install`, then `npm run dev`. Match CI by running `poetry run pytest` and `poetry run mypy` before opening a PR.

## Coding Style & Naming Conventions
Python: 4-space indent, 88-column max, double quotes. Lint and format using `poetry run ruff check --fix`; enforce types with `poetry run mypy`. Follow the service/repository/schema layering already present in each bounded context (e.g., `src/media_processing/services`). TypeScript: respect the Vite ESLint config, using PascalCase for components and camelCase for hooks or utilities.

## Testing Guidelines
Use `poetry run pytest tests/unit` for fast feedback. Mark async tests with `@pytest.mark.asyncio`. Integration flows in `tests/integration` expect Postgres and Redis—bring them up with Docker first. Extend fixture factories from `tests/conftest.py`, and document any long-running scenarios so Stage 6 validation stays reproducible.

### Backend Tests dentro dos Containers
- A imagem `backend` já instala `pytest`, `pytest-asyncio` e `httpx` via `requirements.txt`.
- Para validar rapidamente dentro do Docker: `docker compose exec backend python -m pytest test_db_connection.py -vv` e demais arquivos utilitários (`test_app.py`, etc.).
- Sempre que editar `requirements.txt`, reconstrua os serviços (`docker compose up --build backend worker`).

## MCP Agent Shortcuts
The Codex CLI exposes several MCP servers.
- `context7.resolve-library-id "fastapi"` → `context7.get-library-docs "<id>"` to pull official docs before coding.
- `ddg-search.duckduckgo_web_search "<query>"` for current articles or specs.
- `github.list_branches owner repo` / `github.create_branch owner repo branch` to sync with the `refactor/admin-facade` flow.
- `magicuidesign.getUIComponents` (plus `getButtons`, `getAnimations`) for rapid UI scaffolds.
- `playwright.browser_navigate "https://localhost:8000"` then `browser_wait_for` to script smoke checks.
- `zen.consensus`, `zen.planner`, and `zen.testgen` support plan tracking, analysis, and suite design—run them before large architectural moves.
- `zen.refactor` para encontrar oportunidades de limpeza arquitetural, `zen.thinkdeep` para investigações multi-etapas e `zen.sequentialthinking` para decompor tarefas grandes.
- `mcp-compass.recommend-mcp-servers` ajuda a descobrir MCPs externos, `memory` guarda contexto persistente e o pacote `context7` cobre documentação técnica.
- Use o MCP `github.*` (list/get/create PRs, branches, commits) para automatizar interações com o repositório remoto; comandos `git` locais seguem disponíveis quando for preciso inspecionar a working tree.

## Commit & Pull Request Guidelines
Commits follow Conventional style with context scopes (`refactor(admin): ...`). Keep messages in English, referencing the plan checkpoint (e.g., `Stage6-6.2.1`). PRs must list validation commands, link tracking issues, and add screenshots for UI updates. Ensure `poetry run pytest` and `npm run build` (when UI changes land) are green before requesting review.
