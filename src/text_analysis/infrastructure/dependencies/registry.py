"""Registry central de providers para text_analysis (evita strings mágicas duplicadas)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List

from src.shared.infrastructure.config.settings import settings


@dataclass(slots=True)
class ProviderEntry:
    name: str
    label: str
    description: str
    available: bool = True


# A geração de texto roda só no Ollama: o modelo principal e o de reserva
# vêm das configurações (LLM_MODEL e LLM_FALLBACK_MODEL).
TEXT_GEN_PROVIDERS: List[ProviderEntry] = [
    ProviderEntry(
        name=settings.llm_model,
        label=f"{settings.llm_model} (Ollama)",
        description="Modelo principal do resumo e dos títulos dos temas.",
    ),
    ProviderEntry(
        name=settings.llm_fallback_model,
        label=f"{settings.llm_fallback_model} (Ollama)",
        description="Reserva, usada quando o principal falha.",
    ),
]

# TTL para revalidação de health (segundos)
HEALTH_TTL_SECONDS = int(os.getenv("TEXT_ANALYSIS_HEALTH_TTL", "300"))
_last_health_check: float = 0.0



TOPIC_PROVIDERS: List[ProviderEntry] = [
    ProviderEntry(
        name="bertopic",
        label="BERTopic",
        description="Modelagem de tópicos com BERTopic.",
    ),
    ProviderEntry(
        name="tfidf",
        label="TF-IDF + KMeans",
        description="Fallback leve sem deps pesadas.",
    ),
]

SENTIMENT_PROVIDERS: List[ProviderEntry] = [
    ProviderEntry(
        name="transformers",
        label="Transformers (Sentiment)",
        description="Pipeline transformers para sentimento.",
    )
]


EMBEDDING_PROVIDERS: List[ProviderEntry] = [
    ProviderEntry(
        name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        label="Paraphrase Multilingual MiniLM L12 (v2)",
        description="Padrão atual. Rápido, leve e com bom suporte PT-BR.",
    ),
    ProviderEntry(
        name="intfloat/multilingual-e5-small",
        label="Multilingual E5 Small",
        description="SOTA em benchmarks MTEB. Requer prefixos 'query:'/'passage:' para performance máxima.",
    ),
    ProviderEntry(
        name="intfloat/multilingual-e5-large",
        label="Multilingual E5 Large",
        description="Versão maior do E5. Maior precisão, maior consumo de memória.",
    ),
]


def needs_health_refresh() -> bool:
    return (time.time() - _last_health_check) > HEALTH_TTL_SECONDS


def update_health_timestamp() -> None:
    global _last_health_check
    _last_health_check = time.time()


__all__ = [
    "ProviderEntry",
    "TEXT_GEN_PROVIDERS",
    "TOPIC_PROVIDERS",
    "SENTIMENT_PROVIDERS",
    "EMBEDDING_PROVIDERS",
]
