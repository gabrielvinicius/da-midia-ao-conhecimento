"""Tarefas longas não são reentregues pelo Redis no meio da execução."""
from src.celery_app import create_celery
from src.media_processing.config.settings import processing_settings


def test_visibility_timeout_covers_the_longest_allowed_processing():
    app = create_celery()
    longest = processing_settings.stall_maximum_hours * 3600

    assert app.conf.task_acks_late is True
    assert app.conf.broker_transport_options["visibility_timeout"] > longest
    assert app.conf.result_backend_transport_options["visibility_timeout"] > longest
