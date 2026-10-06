"""Configuração do Celery: reentrega, limites de tempo e montagem dos workers."""
from src.celery_app import create_celery
from src.media_management.config.settings import media_settings
from src.media_processing.config.settings import processing_settings


def test_visibility_timeout_covers_the_longest_allowed_processing():
    app = create_celery()
    longest = processing_settings.stall_maximum_hours * 3600

    assert app.conf.task_acks_late is True
    assert app.conf.broker_transport_options["visibility_timeout"] > longest


def test_results_are_not_stored_and_only_workers_load_their_assembly():
    app = create_celery()

    assert app.conf.task_ignore_result is True
    assert app.conf.result_backend is None
    # Por nome: a API, que importa celery_app para enviar tarefas, não carrega os workers.
    assert "src.worker_process" in app.conf.include


def test_no_attempt_outlives_the_deadlines_that_mark_the_media_as_failed():
    from src.media_processing import tasks as processing
    from src.text_analysis import tasks as analysis

    longest = processing_settings.stall_maximum_hours * 3600
    assert processing.process_transcription_task.time_limit == longest
    assert processing.process_text_extraction_task.time_limit == longest
    # A análise para (e anuncia o motivo) antes que a mídia seja dada como falha pelo prazo.
    assert analysis.analyze_task.soft_time_limit < analysis.analyze_task.time_limit
    assert analysis.analyze_task.time_limit < media_settings.analysis_give_up_minutes * 60
