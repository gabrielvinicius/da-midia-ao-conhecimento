"""Métricas sem ids nos rótulos: uma série por mídia faria o Prometheus crescer sem limite."""
from src.shared.infrastructure.observability.metrics.prometheus_metrics import shared_metrics


def test_no_metric_is_labelled_by_media_or_user():
    metrics = [
        shared_metrics.get_media_operations_total(),
        shared_metrics.get_media_duration_seconds(),
        shared_metrics.get_text_analysis_operations_total(),
        shared_metrics.get_text_analysis_duration_seconds(),
    ]
    for metric in metrics:
        assert not {"media_id", "user_id"} & set(metric._labelnames), metric._name
