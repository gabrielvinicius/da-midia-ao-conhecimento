# Panorama arquitetural (estado em 2025-12)

Visão breve de como a API compõe os bounded contexts, recursos compartilhados e o ciclo de vida em `main.py`.

## Ciclo de vida (`main.lifespan`)
1) Configura logging/OTel.
2) Abre engine + sessão async SQLAlchemy.
3) Cria *event bus* (InMemory, por processo) e executa os bootstraps de cada módulo.
4) Registra dependências/routers via `DEFAULT_MODULE_SPECS` (`shared/application/modules.py`).
5) Conecta cache Redis (quando habilitado) e inicia/desliga o bus no startup/shutdown.

## Módulos e superfícies públicas
| Contexto | Superfície exposta | Integrações chave |
| --- | --- | --- |
| user_management | Services/queries; tokens e hashing via providers no bootstrap | Fornece `UserReadService` p/ notifications/admin |
| media_management | `MediaModule`, `MediaAdminContext`; `MediaService` é entrada única | Usa `StorageServiceFactory` (storage BC) e publica `MediaUploaded` |
| media_processing | Services de vídeo/transcrição/texto; schedulers Celery ficam em `application/tasks.py` | Assina `MediaUploaded`; depende de providers via registries e de `StorageServiceFactory` |
| text_analysis | `TextAnalysisModule` (text, summarize, sentiment, topic) | Consome `TextContentReady`/`MediaUploaded`; ports próprios p/ transcriptions/embeddings/event bus |
| notifications | `NotificationModule` | Assina `NotificationRequested`; usa ports de delivery/metrics/logging e `AuthQueriesPort` (fornecido pelo `UserReadService`) |
| admin | `AdminModule` | Fachada sobre ports de mídia/usuários; adapters em `admin/infrastructure/adapters` |
| storage (técnico) | Ports em `storage/application/ports.py`; adapters locais/S3-stub em `storage/infrastructure/adapters`; fábrica `StorageServiceFactory` | Consumido por media_* e pipelines de texto |
| shared (cross-cutting) | Event bus, cache, observability ports (logger/metrics), middleware | Não contém adapters de storage (removido); apenas contratos/utilidades |

## Event bus
- `InMemoryEventBus` é criado por processo (`event_bus_factory.get_event_bus`). API o guarda em `app.state`; workers Celery criam sua instância (variáveis `EVENT_BUS` em tasks).
- Providers `get_event_bus` não usam singletons implícitos; preferir passar o bus pelo bootstrap. Fallback a `resolve_event_bus()` só quando explicitamente necessário.
- Eventos principais: `MediaUploaded`, `TextContentReady`, `NotificationRequested`. Handlers registrados nos bootstraps de media_processing, text_analysis e notifications.

## Tarefas Celery
- Entrypoints e schedulers em `src/media_processing/application/tasks.py` (text, transcription, video) e `src/text_analysis/tasks.py`; notifications em `src/notifications/application/tasks.py`.
- Bootstraps de worker concentram composição de serviços (deps, repos, métricas, bus): `media_processing/application/worker_bootstrap.py`, `text_analysis/worker_bootstrap.py`, `notifications/worker_bootstrap.py`.
- Payloads validados com Pydantic v2 nos schemas de cada módulo.

## Storage
- Contratos únicos em `storage/application/ports.py` (provider/repo/logger/metrics/file port).
- Adapters: `local` e `s3` (stub) em `storage/infrastructure/adapters`; fábrica em `storage/infrastructure/dependencies.py`.
- `media_management` e pipelines de texto/vídeo consomem storage via factory (sem aliases em shared).

## Observabilidade
- Ports em `shared/infrastructure/observability/ports.py` (logger/metrics).
- Adapters específicos por contexto em `infrastructure/logging/` de cada módulo (ex.: transcription logger, storage logger).
- Métricas Prometheus locais por módulo (`infrastructure/metrics`).

## Testes
- Unit + smoke verdes localmente (`poetry run pytest tests/unit -q`, `tests/smoke -q`).
- Integração depende de Postgres/Redis/Celery ativos.

## Convenções
- Bootstraps em `src/*/bootstrap.py` definem containers e binders de FastAPI.
- Routers montados via `include_module_routers` a partir de `DEFAULT_MODULE_SPECS`.
- Sem módulos legacy `monitoring`/`providers`; loggers/storage centralizados conforme acima.
