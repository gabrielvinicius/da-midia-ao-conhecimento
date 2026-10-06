"""Nomes das tarefas e das filas do Celery, compartilhados entre os módulos.

Quem agenda uma tarefa usa o nome, sem importar o módulo que a executa. As
filas também ficam aqui; o docker-compose repete os nomes no -Q de cada
worker, e um teste confere que as duas listas não se afastam.
"""

TASK_MEDIA_TRANSCRIPTION = "media_processing.transcription"
TASK_MEDIA_TEXT_EXTRACTION = "media_processing.text_extraction"
TASK_MEDIA_SWEEP_STALLED = "media_processing.sweep_stalled"
TASK_MEDIA_RECOVER_UNSTARTED = "media_management.recover_unstarted"
TASK_TEXT_ANALYSIS_ANALYZE = "text_analysis.analyze"

# Worker pesado (GPU), uma tarefa por vez.
QUEUE_TRANSCRIPTION_FAST = "transcription_fast_lane"  # arquivos pequenos passam à frente
QUEUE_TRANSCRIPTION = "transcription_queue"
QUEUE_TEXT_ANALYSIS = "text_analysis_queue"  # análise e extração de texto (OCR)
HEAVY_WORKER_QUEUES = (QUEUE_TRANSCRIPTION_FAST, QUEUE_TRANSCRIPTION, QUEUE_TEXT_ANALYSIS)

# Worker leve: verificações periódicas (beat).
QUEUE_MAINTENANCE = "celery"
LIGHT_WORKER_QUEUES = (QUEUE_MAINTENANCE,)
