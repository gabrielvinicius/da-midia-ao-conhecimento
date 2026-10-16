<!-- Gerado por scripts/docs/gerar_referencia.py a partir do código. Não edite à mão: rode o script. -->

# Referência dos eventos e das filas

Os módulos conversam por **eventos de integração** (`src/shared/domain/events.py`). Cada evento tem um único módulo que o publica; os demais só reagem a ele. Dentro de um processo, o barramento em memória entrega o evento às reações inscritas; entre a API e os workers, o trabalho segue pelas **filas** do Celery (Redis). Veja [Arquitetura](../explicacao/arquitetura.md) e [Pipeline de processamento](../explicacao/pipeline.md).

Todo evento carrega também `event_id`, `occurred_at` e `correlation_id` (o identificador da requisição que o originou, presente em todos os logs).

## Eventos

| Evento | Publicado por | Reações nos workers | Campos |
|---|---|---|---|
| `MediaUploaded` | `media_management` | `media_processing` | `media_id`, `user_id`, `filename`, `media_type`, `storage_provider`, `transcription_provider`, `file_path`, `file_size_bytes`, `language` |
| `MediaDeleted` | `media_management` | — | `media_id`, `reason`, `user_id`, `triggered_by`, `actor_id` |
| `MediaReprocessRequested` | `media_management` | — | `media_id`, `triggered_by`, `actor_id`, `requested_by`, `note` |
| `MediaFailed`<br>A mídia foi dada como falha pelo próprio módulo de mídias (ex.: o processamento nunca começou). | `media_management` | `notifications` | `media_id`, `user_id`, `stage`, `error_message` |
| `MediaProcessingStarted` | `media_processing` | `media_management` | `media_id`, `stage` |
| `MediaProcessingCompleted` | `media_processing` | — | `media_id`, `stage`, `result_id`, `provider` |
| `MediaProcessingFailed` | `media_processing` | `media_management`, `notifications` | `media_id`, `stage`, `error_message`, `user_id` |
| `TranscriptionCompleted` | `media_processing` | `media_management`, `notifications` | `media_id`, `transcription_id`, `text`, `user_id`, `provider`, `language`, `confidence`, `filename` |
| `TranscriptionFailed` | `media_processing` | `media_management`, `notifications` | `media_id`, `transcription_id`, `user_id`, `error_message`, `provider` |
| `TextContentReady` | `media_management` | `media_processing` | `media_id`, `transcription_id`, `text`, `user_id`, `filename`, `language` |
| `AnalysisCompleted`<br>Fim da análise de uma mídia. É o ponto de entrada de novas camadas (avisos hoje; catálogo e tendências depois): traz o que a análise achou em campos simples, sem obrigar quem reage a ler a análise inteira. | `text_analysis` | `media_management`, `notifications` | `analysis_id`, `media_id`, `transcription_id`, `user_id`, `summary_source`, `overall_sentiment`, `topic_titles`, `failed_steps` |
| `AnalysisFailed`<br>A análise falhou de vez (última tentativa ou erro que não passa sozinho). | `text_analysis` | `media_management`, `notifications` | `media_id`, `transcription_id`, `user_id`, `error_message` |

## Tarefas do Celery

Nomes em `src/shared/events/integration_events.py`; quem agenda uma tarefa usa o nome, sem importar o módulo que a executa.

| Constante | Tarefa |
|---|---|
| `TASK_MEDIA_TRANSCRIPTION` | `media_processing.transcription` |
| `TASK_MEDIA_TEXT_EXTRACTION` | `media_processing.text_extraction` |
| `TASK_MEDIA_SWEEP_STALLED` | `media_processing.sweep_stalled` |
| `TASK_MEDIA_RECOVER_UNSTARTED` | `media_management.recover_unstarted` |
| `TASK_TEXT_ANALYSIS_ANALYZE` | `text_analysis.analyze` |

## Filas

O `-Q` de cada worker no `docker-compose.yml` repete estas listas, e um teste (`tests/unit/test_queue_names.py`) confere que as duas não se afastam.

| Worker | Filas, em ordem de prioridade |
|---|---|
| `worker-heavy` (GPU, uma tarefa por vez) | `transcription_fast_lane`, `transcription_queue`, `text_analysis_queue` |
| `worker-light` (verificações periódicas) | `celery` |
