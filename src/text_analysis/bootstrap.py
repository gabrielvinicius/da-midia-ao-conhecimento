"""Bootstrap and binding helpers for the text_analysis module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from fastapi import FastAPI

from .application.ports import TranscriptionQueryPort
from .application.services.analysis_request_service import AnalysisRequestService
from .application.services.analysis_review_service import AnalysisReviewService
from .application.services.knowledge_base_service import KnowledgeBaseService
from .application.services.text_analysis_read_service import TextAnalysisReadService
from .infrastructure.dependencies import registry as ta_registry
from .infrastructure.dependencies.builders import (
    build_analysis_read_service,
    build_analysis_request_service,
    build_analysis_review_service,
    build_knowledge_service,
)
from .infrastructure.dependencies.registry import needs_health_refresh, update_health_timestamp
from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.observability.metrics.prometheus_metrics import SharedPrometheusMetrics

try:
    import httpx  # noqa: F401
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


def _prom_available() -> bool:
    try:
        import prometheus_client  # noqa: F401
        return True
    except Exception:
        return False


@dataclass
class TextAnalysisModule:
    """Serviços da API: leitura, revisão, pedido de análise e busca.

    A análise roda no worker; a API não monta o pipeline nem carrega modelos.
    """

    read_service: TextAnalysisReadService
    review_service: AnalysisReviewService
    request_service: AnalysisRequestService
    knowledge_service: KnowledgeBaseService


async def build_text_analysis_module(
    session: Any,
    repository: Any | None = None,
    transcription_queries: Optional[TranscriptionQueryPort] = None,
    **_kwargs: Any,
) -> TextAnalysisModule:
    """Módulo da API, montado uma vez (sessão por requisição) pelas fábricas únicas.

    A análise em si roda no worker: a API não assina TextContentReady.
    """
    if session is None and repository is None:
        raise RuntimeError("TextAnalysis requires a database session for persistence")
    _update_registry_availability()
    return TextAnalysisModule(
        read_service=build_analysis_read_service(session, repository=repository),
        review_service=build_analysis_review_service(session, repository=repository),
        request_service=build_analysis_request_service(session, transcription_queries=transcription_queries),
        knowledge_service=build_knowledge_service(session),
    )


def bind_text_analysis_module(app: FastAPI, module: TextAnalysisModule) -> None:
    """Register dependency overrides for text analysis."""
    from .api.dependencies import (
        get_analysis_read_service,
        get_analysis_request_service,
        get_analysis_review_service,
        get_knowledge_service,
    )

    app.dependency_overrides[get_analysis_read_service] = lambda: module.read_service
    app.dependency_overrides[get_analysis_review_service] = lambda: module.review_service
    app.dependency_overrides[get_analysis_request_service] = lambda: module.request_service
    app.dependency_overrides[get_knowledge_service] = lambda: module.knowledge_service


def _check_module_available(module_name: str) -> bool:
    """Helper to check if a heavy module is available without polluting sys.modules."""
    import importlib.util
    return importlib.util.find_spec(module_name) is not None


def _update_registry_availability() -> None:
    """Marca disponibilidade no registry sem carregar modelos pesados."""
    if not needs_health_refresh():
        return

    metrics = SharedPrometheusMetrics().get_provider_health_checks_total()

    # Ollama: ping /api/tags com timeout curto
    ollama_ok = False
    if httpx:
        try:  # pragma: no cover - ambiente externo
            with httpx.Client(timeout=1.5) as client:
                # O endereço vem das configurações: no Docker, o Ollama é
                # outro contêiner, e localhost o daria sempre como fora do ar.
                resp = client.get(f"{settings.ollama_host.rstrip('/')}/api/tags")
                resp.raise_for_status()
                ollama_ok = True
        except Exception:
            ollama_ok = False
    for entry in ta_registry.TEXT_GEN_PROVIDERS:
        entry.available = ollama_ok
    metrics.labels(provider_type="textgen_ollama", status="up" if ollama_ok else "down").inc()

    # Topic modeling
    bertopic_ok = _check_module_available("bertopic")
    for entry in ta_registry.TOPIC_PROVIDERS:
        if entry.name == "bertopic":
            entry.available = bertopic_ok
            metrics.labels(provider_type="topic_bertopic", status="up" if bertopic_ok else "down").inc()

    # TF-IDF deps
    tfidf_ok = _check_module_available("sklearn") and _check_module_available("numpy")
    for entry in ta_registry.TOPIC_PROVIDERS:
        if entry.name == "tfidf":
            entry.available = tfidf_ok
            metrics.labels(provider_type="topic_tfidf", status="up" if tfidf_ok else "down").inc()

    update_health_timestamp()