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
        name="hf:NousResearch/Meta-Llama-3.1-8B-Instruct",
        label="Llama 3.1 8B (NousResearch)",
        description="Versão aberta do Llama 3.1, sem restrições de acesso.",
        target="hf:NousResearch/Meta-Llama-3.1-8B-Instruct",
    ),
    ProviderEntry(
        name="hf:mistralai/Mistral-Nemo-Instruct-v1",
        label="Mistral Nemo 12B (SOTA Raciocínio)",
        description="Recomendado para 12GB+ VRAM. Raciocínio superior ao Llama 8B. Requer 4-bit quantization.",
        target="hf:mistralai/Mistral-Nemo-Instruct-v1",
    ),
    ProviderEntry(
        name="hf:nvidia/Nemotron-Orchestrator-8B",
        label="NVIDIA Nemotron 8B",
        description="Especialista em orquestração e análise técnica profunda.",
        target="hf:nvidia/Nemotron-Orchestrator-8B",
    ),
    ProviderEntry(
        name="hf:DavidAU/Llama3.3-8B-Instruct-Thinking-Heretic-Uncensored-Claude-4.5-Opus-High-Reasoning",
        label="Llama 3.3 Heretic (High Reasoning)",
        description="Modelo uncensored com raciocínio extremo e lógica avançada.",
        target="hf:DavidAU/Llama3.3-8B-Instruct-Thinking-Heretic-Uncensored-Claude-4.5-Opus-High-Reasoning",
    ),
    ProviderEntry(
        name="hf:meta-llama/Llama-3.1-8B-Instruct",
        label="Llama 3.1 8B (Transformers/HF)",
        description="Versão atualizada com melhor raciocínio e contexto expandido.",
        target="hf:meta-llama/Llama-3.1-8B-Instruct",
    ),
    ProviderEntry(
        name="hf:meta-llama/Meta-Llama-3-8B-Instruct",
        label="Llama 3 8B (Transformers/HF)",
        description="Qualidade alta; preferir quantização em 12GB.",
        target="hf:meta-llama/Meta-Llama-3-8B-Instruct",
    ),
    ProviderEntry(
        name="hf:NousResearch/Meta-Llama-3-8B-Instruct",
        label="Llama 3 8B (NousResearch)",
        description="Versão aberta do Llama 3, alta qualidade e sem restrições de acesso.",
        target="hf:NousResearch/Meta-Llama-3-8B-Instruct",
    ),
    ProviderEntry(
        name="hf:microsoft/Phi-3-mini-4k-instruct",
        label="Phi-3 Mini 4k (Transformers/HF)",
        description="Leve e rápido; excelente para summaries em CPU/GPU.",
        target="hf:microsoft/Phi-3-mini-4k-instruct",
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
        name="hf:Qwen/Qwen2.5-3B-Instruct",
        label="Qwen 2.5 3B (Instruct)",
        description="Melhor modelo pequeno atual (SOTA < 7B). Excelente suporte a Português.",
        target="hf:Qwen/Qwen2.5-3B-Instruct",
    ),
    ProviderEntry(
        name="hf:Qwen/Qwen2.5-7B-Instruct",
        label="Qwen 2.5 7B (Instruct)",
        description="Modelo 7B extremamente capaz, supera muitos 13B.",
        target="hf:Qwen/Qwen2.5-7B-Instruct",
    ),
    ProviderEntry(
        name="hf:Qwen/Qwen2-7B-Instruct",
        label="Qwen2 7B (Transformers/HF)",
        description="Multilíngue forte; bom custo/benefício.",
        target="hf:Qwen/Qwen2-7B-Instruct",
    ),
]

TEXT_GEN_ROUTING: Mapping[str, str] = {
    # nomes amigáveis -> destino transformers
    "qwen": "hf:Qwen/Qwen2.5-3B-Instruct",
    "qwen-7b": "hf:Qwen/Qwen2.5-7B-Instruct",
    "nemo": "hf:mistralai/Mistral-Nemo-Instruct-v1",
    "nemotron": "hf:nvidia/Nemotron-Orchestrator-8B",
    "llama3.3-heretic": "hf:DavidAU/Llama3.3-8B-Instruct-Thinking-Heretic-Uncensored-Claude-4.5-Opus-High-Reasoning",
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
    "EMBEDDING_PROVIDERS",
    "resolve_textgen_target",
    "STOPWORDS_LANGS",
]
