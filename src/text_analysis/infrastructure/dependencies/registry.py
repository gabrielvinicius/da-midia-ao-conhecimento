"""Registry central de providers para text_analysis (evita strings mágicas duplicadas)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(slots=True)
class ProviderEntry:
    name: str
    label: str
    description: str
    available: bool = True
    target: Optional[str] = None  # para transformers/ollama


TEXT_GEN_PROVIDERS: List[ProviderEntry] = [
    ProviderEntry(
        name="hf:mistralai/Mistral-7B-Instruct-v0.3",
        label="Mistral 7B (Transformers/HF)",
        description="Equilíbrio qualidade/VRAM; use 8-bit/4-bit em 12GB.",
        target="hf:mistralai/Mistral-7B-Instruct-v0.3",
    ),
    ProviderEntry(
        name="hf:meta-llama/Meta-Llama-3-8B-Instruct",
        label="Llama 3 8B (Transformers/HF)",
        description="Qualidade alta; preferir quantização em 12GB.",
        target="hf:meta-llama/Meta-Llama-3-8B-Instruct",
    ),
    ProviderEntry(
        name="hf:microsoft/Phi-3-small-8k-instruct",
        label="Phi-3 Small (Transformers/HF)",
        description="Leve e rápido; bom fallback em CPU.",
        target="hf:microsoft/Phi-3-small-8k-instruct",
    ),
    ProviderEntry(
        name="hf:google/gemma-2-9b-it",
        label="Gemma 2 9B (Transformers/HF)",
        description="Melhor PT/EN; ideal quantizado.",
        target="hf:google/gemma-2-9b-it",
    ),
    ProviderEntry(
        name="hf:Qwen/Qwen2-7B-Instruct",
        label="Qwen2 7B (Transformers/HF)",
        description="Multilíngue forte; bom custo/benefício.",
        target="hf:Qwen/Qwen2-7B-Instruct",
    ),
    ProviderEntry(
        name="ollama:llama3:8b",
        label="Llama3 8B (Ollama)",
        description="Servido via Ollama (gguf).",
        target="ollama:llama3:8b",
    ),
    ProviderEntry(
        name="ollama:mistral",
        label="Mistral 7B (Ollama)",
        description="Opção leve servida pelo Ollama.",
        target="ollama:mistral",
    ),
    ProviderEntry(
        name="ollama:phi3:mini",
        label="Phi-3 Mini (Ollama)",
        description="Extremamente leve; ideal em CPU.",
        target="ollama:phi3:mini",
    ),
]

TEXT_GEN_ROUTING: Mapping[str, str] = {
    # nomes amigáveis -> destino transformers
    "mistral-7b": "hf:mistralai/Mistral-7B-Instruct-v0.3",
    "phi3-small": "hf:microsoft/Phi-3-small-8k-instruct",
    "gemma2-9b": "hf:google/gemma-2-9b-it",
    "qwen2-7b": "hf:Qwen/Qwen2-7B-Instruct",
    # llama3 permanece com adapter dedicado, mas normalizamos alias
    "llama3": "llama3",
}

# TTL para revalidação de health (segundos)
HEALTH_TTL_SECONDS = int(os.getenv("TEXT_ANALYSIS_HEALTH_TTL", "300"))
_last_health_check: float = 0.0

# idiomas suportados para stopwords (tfidf); configurável via env
_DEFAULT_STOPWORDS = {"english", "portuguese", "spanish"}
_ENV_STOPWORDS = {
    lang.strip().lower()
    for lang in os.getenv("TEXT_ANALYSIS_STOPWORDS_LANGS", "").split(",")
    if lang.strip()
}
STOPWORDS_LANGS = _DEFAULT_STOPWORDS | _ENV_STOPWORDS


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


def resolve_textgen_target(name: str) -> str:
    """Mapeia nome amigável para repo real; retorna o próprio se não houver."""
    aliases: Dict[str, str] = {k: v for k, v in TEXT_GEN_ROUTING.items() if v.startswith("hf:")}
    return aliases.get(name, name)


def validate_textgen_name(name: str) -> bool:
    """Verifica se o nome está listado no registry (providers ou aliases)."""
    names = {p.name for p in TEXT_GEN_PROVIDERS}
    names.update(TEXT_GEN_ROUTING.keys())
    names.update(TEXT_GEN_ROUTING.values())
    return name in names


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
    "resolve_textgen_target",
    "STOPWORDS_LANGS",
]
