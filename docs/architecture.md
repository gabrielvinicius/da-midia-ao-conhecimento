# Panorama arquitetural

Este documento resume como a API orquestra seus *bounded contexts* e os
recursos compartilhados. Ele descreve o ciclo de vida real da aplicação,
como cada módulo é montado via as fábricas em `src/*/bootstrap.py`, e como
o mecanismo de overrides garante que os routers FastAPI recebam as
dependências corretas.

## Ciclo de vida da aplicação (`main.lifespan`)

O ponto de entrada `main.py` define um gerenciador de ciclo de vida que
executa toda a composição da aplicação a cada inicialização e garante o
*shutdown* limpo dos recursos assíncronos.【F:main.py†L45-L129】 As etapas
principais são:

1. **Observabilidade** – aplica configuração de *logging* estruturado e
   OpenTelemetry antes de instanciar qualquer recurso de domínio.【F:main.py†L49-L63】
2. **Banco de dados** – garante que o esquema esteja criado executando
   `Base.metadata.create_all` dentro de uma sessão assíncrona.【F:main.py†L65-L70】
3. **Fábricas de módulo** – cria uma sessão SQLAlchemy única e instancia o
   *event bus*, que é reaproveitado em todo o ciclo de vida. Em seguida,
   executa as fábricas de cada contexto (auth, monitoring, media,
   transcription, etc.), configurando contêineres com todas as dependências
   concretas.【F:main.py†L72-L118】
4. **Overrides FastAPI** – chama `register_module_dependencies` para ligar
   cada função de dependência do FastAPI às instâncias produzidas pelas
   fábricas (detalhes na seção seguinte).【F:main.py†L120-L129】【F:src/shared/application/modules.py†L42-L109】
5. **Recursos compartilhados** – registra o *event bus* e o cliente de
   cache global em `ApplicationResources`, iniciando o *listener* do bus e
   abrindo a conexão Redis durante o *startup*. No *shutdown* o processo é
   revertido e o engine SQLAlchemy é liberado.【F:main.py†L131-L149】【F:src/shared/application/lifecycle.py†L17-L39】

Esse ciclo de vida evita estados globais ocultos: cada módulo recebe a
sessão ativa explicitamente, enquanto os recursos transversais (event bus e
cache) são ligados ao aplicativo via `app.state` e ao gerenciador de ciclo
de vida.

## Fábricas de módulo em `src/*/bootstrap.py`

Cada *bounded context* expõe um arquivo `bootstrap.py` que cumpre três
papéis consistentes:

1. **Container declarativo** – composto com `dependency_injector`, recebe
   as dependências externas (sessão do banco, *event bus*, *task
   schedulers*, *connection managers* etc.) e registra implementações
   concretas.【F:src/media_management/bootstrap.py†L25-L105】【F:src/media_processing/transcription/bootstrap.py†L21-L52】
2. **`dataclass` de módulo** – define a superfície pública do contexto,
   expondo apenas os serviços, *queries* e *command handlers* necessários
   para interação com routers ou outros módulos.【F:src/media_management/bootstrap.py†L107-L127】【F:src/text_analysis/summarization/bootstrap.py†L51-L67】
3. **Funções de composição** – `create_*_container`/`build_*_module`
   recebem as dependências externas, materializam o container e, quando
   necessário, registram *event handlers* adicionais ligados ao *event
   bus*.【F:src/text_analysis/summarization/bootstrap.py†L69-L113】【F:src/media_processing/transcription/bootstrap.py†L54-L88】【F:src/media_processing/video_processing/bootstrap.py†L43-L76】

A tabela abaixo resume os módulos principais e suas integrações diretas:

| Contexto | Superfície exposta | Integrações notáveis |
| --- | --- | --- |
| `auth` | `AuthModule` com serviços e *queries* de autenticação | Apenas depende da sessão; fornece *queries* para outros módulos como `notifications` e `admin`.【F:src/auth/bootstrap.py†L1-L28】【F:main.py†L88-L100】 |
| `media_management` | `MediaModule` e `MediaAdminContext` | Usa storage abstraído, métricas e *event bus* para publicar `MediaUploaded` via `DefaultMediaEventPublisher`.【F:src/media_management/bootstrap.py†L25-L167】【F:src/media_management/application/commands/components/event_publisher.py†L1-L32】 |
| `media_processing` | `MediaProcessingService` + módulos `video_processing`/`transcription` | Concentra a orquestração de extração de áudio, thumbnails e geração de transcrições, agendando tarefas Celery ao consumir `MediaUploaded`.【F:src/media_processing/application/services.py†L1-L144】【F:src/media_processing/video_processing/bootstrap.py†L1-L76】【F:src/media_processing/transcription/bootstrap.py†L21-L88】 |
| `text_analysis` | `TextAnalysisModule` e submódulos (`text_processing`, `summarization`, `sentiment_analysis`, `topic_modeling`) | Pipeline consolidado para processar texto, sumarizar, analisar sentimento e modelar tópicos, reaproveitando o mesmo container e tarefas Celery. 【F:src/text_analysis/bootstrap.py†L1-L120】【F:src/text_analysis/text_processing/bootstrap.py†L1-L74】【F:src/text_analysis/summarization/bootstrap.py†L21-L113】 |
| `notifications` | `NotificationModule` | Conecta-se ao *event bus* e ao `ConnectionManager`, expondo serviço e repositório; assina `NotificationRequested`.【F:src/notifications/bootstrap.py†L1-L73】【F:src/notifications/application/event_handlers.py†L11-L37】 |
| `admin` | `AdminModule` | Reúne serviços de usuários, mídia e auditoria para os routers administrativos.【F:main.py†L107-L118】【F:src/admin/bootstrap.py†L1-L60】 |
| `admin` | `AdminModule` | Reúne serviços de usuários, mídia e auditoria para os routers administrativos.【F:main.py†L107-L118】【F:src/admin/bootstrap.py†L1-L60】 |

Essa padronização facilita a reutilização dos módulos dentro da aplicação
monolítica e estabelece limites claros entre escrita (commands) e leitura
(*queries*).

## Overrides de dependência compartilhados

`register_module_dependencies` é a única função responsável por ligar as
dependências do FastAPI às instâncias criadas no bootstrap. Ela mapeia cada
`get_*_dependencies` para um objeto com os serviços necessários,
substituindo as implementações padrão com *overrides* no objeto FastAPI.【F:src/shared/application/modules.py†L42-L109】

Esse mecanismo permite que os routers permaneçam desacoplados das
implementações concretas. Exemplo: `get_media_dependencies` passa a
retornar a combinação de `MediaQueries`, `MediaUploadService` e
`MediaLifecycleService` produzidos pelo container configurado no `lifespan`
ao invés de instanciar serviços diretamente.

## Event bus e conexões entre contextos

O `EventBus` centraliza a orquestração dos eventos de domínio. Ele aceita
handlers assíncronos, publica os eventos na fila configurada e garante o
despacho local para todos os assinantes registrados.【F:src/shared/events/event_bus.py†L1-L93】 O mesmo objeto fica em `app.state`
e é iniciado/detido junto com a aplicação através de
`start_application_resources`/`stop_application_resources`.【F:main.py†L129-L149】【F:src/shared/application/lifecycle.py†L17-L39】

As integrações por contexto ficam assim:

| Contexto | Publica via event bus | Assina via event bus |
| --- | --- | --- |
| `media_management` | `MediaUploaded` ao concluir `CreateMediaCommandHandler` (via `DefaultMediaEventPublisher`).【F:src/media_management/application/commands/create_media_command_handler.py†L84-L145】【F:src/media_management/application/commands/components/event_publisher.py†L1-L32】 | — |
| `media_processing` | — | `MediaUploaded` para acionar extração de áudio, geração de thumbnails e transcrições via Celery.【F:src/media_processing/video_processing/application/event_handlers.py†L17-L37】【F:src/media_processing/transcription/application/event_handlers.py†L38-L125】 |
| `text_analysis` | — | `MediaUploaded` e `TextContentReady` para pipelines de processamento textual, sumarização, sentimento e tópicos. Cada submódulo agenda tarefas Celery especializadas.【F:src/text_analysis/text_processing/application/event_handlers.py†L13-L43】【F:src/text_analysis/summarization/application/event_handlers.py†L13-L46】【F:src/text_analysis/sentiment_analysis/application/event_handlers.py†L11-L39】【F:src/text_analysis/topic_modeling/application/event_handlers.py†L11-L36】 |
| `notifications` | — | `NotificationRequested`, convertendo o evento em tarefas Celery que enviam mensagens nos canais configurados.【F:src/notifications/application/event_handlers.py†L11-L37】 |

Outros contextos (auth, providers, monitoring, admin) não usam o *event bus*
diretamente no código atual, mas podem consumir os eventos acima através dos
overrides compartilhados sempre que necessário. Os tipos de evento residem
em `src/shared/events/domain_events.py`, permitindo expandir o fluxo sem
acoplar módulos adicionais.【F:src/shared/events/domain_events.py†L34-L118】

Por padrão o *event bus* utiliza implementações in-memory, mas `get_event_bus`
suporta troca de *broker* e estratégia de assinatura via `EventBusConfig`,
cacheando instâncias para evitar recreações desnecessárias.【F:src/shared/events/event_bus.py†L95-L143】

## Cache distribuído e uso cross-contexto

`src/shared/infrastructure/cache.py` implementa um cliente Redis assíncrono
(`RedisCache`) com estratégias de TTL, serialização automática e operações
de *pattern delete*. O módulo também expõe `CacheManager`, responsável por
funções de alto nível (cache de mídia, usuários, rate limiting).【F:src/shared/infrastructure/cache.py†L1-L266】【F:src/shared/infrastructure/cache.py†L268-L333】

No ciclo de vida da aplicação, o objeto global `cache` é conectado no
*startup* e desconectado no *shutdown*, garantindo que a conexão com Redis
seja reutilizada em todas as requisições.【F:src/shared/infrastructure/cache.py†L265-L322】【F:src/shared/application/lifecycle.py†L25-L39】 Além de ser
utilizado em *health checks*, o `CacheManager` está disponível para os
módulos que precisarem de caching de consultas, invalidação de mídia ou
aplicação de rate limiting.

## Stage6 – Estado em 03/11/2025

### Consolidação de módulos
- `text_analysis`: o router consolidado (`text_analysis.api.routers`) já substitui o registro direto dos módulos legados em `main.py`. O bootstrap injeta o `TextAnalysisService` nos submódulos de sumarização, sentimento e tópicos, que agora agendam tarefas assíncronas e retornam apenas ACKs (`task_id`) nos fluxos `POST /summaries/reprocess`, `POST /sentiment-analysis/analyze`, `POST /sentiment-analysis/reprocess`, `POST /topic-modeling/analyze` e `POST /topic-modeling/reprocess`.
- `media_processing`: permanece em transição; tasks continuam com lógica de domínio e precisam ser movidas para o `MediaProcessingService` durante a Fase 2.
- `admin`: a fachada continua ativa, porém ainda coexistem caminhos alternativos em módulos herdados. A limpeza final depende da conclusão das etapas acima.

### Event bus + Celery
- O `InMemoryEventBus` segue registrado em `main.py` com handlers reais para `MediaUploaded`, `TextContentReady` e `NotificationRequested`. As tasks Celery ainda carregam lógica de domínio; o objetivo da próxima fase é restringi-las a trabalho pesado (I/O) conforme boas práticas oficiais (`/celery/celery`). citecontext7/celery

### Organização FastAPI
- `main.py` importa apenas routers consolidados (`auth`, `media`, `text_analysis`, `notifications`, `admin`, `monitoring`, `providers`), alinhado às recomendações do FastAPI para modularização. citecontext7/fastapi
- `StorageServiceFactory` já é importado de `src.storage.infrastructure.dependencies`, eliminando o `NameError` registrado no baseline anterior.

### Testes e observabilidade
- `pytest`, `mypy` e `ruff` permanecem desabilitados neste branch. A reativação desses guardrails é requisito para encerrar a Fase 1.
- Métricas Prometheus e spans OpenTelemetry ainda não refletem o novo fluxo híbrido; ajustes serão feitos após a consolidação dos handlers.

### Governança de PRs
- Cada etapa Stage6 deve abrir PR incremental derivado de `refactor/admin-facade`, com checklist mínimo: testes (quando disponíveis), lint, documentação atualizada e plano de rollback.
- Esta seção deve ser revisada ao final de cada fase para manter o alinhamento entre documentação e código.

