"""Static provider metadata for display purposes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .interfaces import ProviderType


@dataclass(frozen=True)
class ProviderMetadata:
    label: str
    description: str


ProviderMetadataMap = Dict[str, ProviderMetadata]


def _build_map() -> Dict[ProviderType, ProviderMetadataMap]:
    """Centralized metadata used by API responses and UI helpers."""

    return {
        ProviderType.STORAGE: {
            "local": ProviderMetadata(
                label="Armazenamento Local",
                description="Armazena arquivos no disco local do servidor.",
            ),
            "s3": ProviderMetadata(
                label="Amazon S3",
                description="Bucket S3 com versionamento/opcionais de criptografia.",
            ),
            "minio": ProviderMetadata(
                label="MinIO",
                description="Compatível com S3, ideal para ambientes self-hosted.",
            ),
        },
        ProviderType.TRANSCRIPTION: {
            "fastwhisper": ProviderMetadata(
                label="FastWhisper",
                description="Inferência Whisper otimizada com CTranslate2 e auto detecção de idioma.",
            ),
            "whisper": ProviderMetadata(
                label="OpenAI Whisper",
                description="Whisper oficial para áudios longos em múltiplos idiomas.",
            ),
            "huggingface": ProviderMetadata(
                label="Transformers ASR",
                description="Modelos HuggingFace Automatic Speech Recognition customizáveis.",
            ),
        },
        ProviderType.SUMMARIZATION: {
            "heuristic_interpretive": ProviderMetadata(
                label="Resumo Interpretativo",
                description="TextRank + contexto temporal, sem dependências externas.",
            ),
            "keyword_highlighter": ProviderMetadata(
                label="Resumo por Palavras-chave",
                description="Seleciona frases com maior densidade de termos relevantes.",
            ),
            "huggingface": ProviderMetadata(
                label="HuggingFace (auto)",
                description="Modelos T5/BART padrão — requer transformers instalados.",
            ),
            "huggingface_t5_base": ProviderMetadata(
                label="HuggingFace T5 Base",
                description="Modelo T5-base focado em resumos curtos PT/EN.",
            ),
            "huggingface_bart_large": ProviderMetadata(
                label="HuggingFace BART Large",
                description="BART-Large CNN — resumos detalhados (inglês).",
            ),
            "huggingface_pegasus": ProviderMetadata(
                label="HuggingFace Pegasus",
                description="Pegasus XSum — ideal para textos longos multi-idioma.",
            ),
            "openai": ProviderMetadata(
                label="OpenAI GPT",
                description="Resumo abstrativo via APIs GPT (cobrança por token).",
            ),
            "embedding_hybrid": ProviderMetadata(
                label="Resumo Híbrido por Embeddings",
                description="Combina TF-IDF + embeddings para narrativas densas.",
            ),
        },
        ProviderType.SENTIMENT_ANALYSIS: {
            "transformers": ProviderMetadata(
                label="Transformers Sentiment",
                description="Pipeline HuggingFace para sentimento multilíngue.",
            ),
            "vader": ProviderMetadata(
                label="VADER",
                description="Léxico otimizado para textos curtos em inglês.",
            ),
        },
        ProviderType.TOPIC_MODELING: {
            "sklearn_lda": ProviderMetadata(
                label="Scikit-Learn LDA",
                description="Modelo probabilístico equilibrado para textos longos.",
            ),
            "sklearn_lsa": ProviderMetadata(
                label="SVD (LSA)",
                description="Redução SVD captura temas globais.",
            ),
            "sklearn_nmf": ProviderMetadata(
                label="NMF Localizado",
                description="Foca em padrões específicos de cada tópico.",
            ),
            "keyword_frequency": ProviderMetadata(
                label="Frequência de Palavras",
                description="Fallback leve sem dependências externas.",
            ),
            "btm_simple": ProviderMetadata(
                label="BTM Simplificado",
                description="Ideal para conversas curtas e chats.",
            ),
            "anchor_topics": ProviderMetadata(
                label="Tópicos por Âncoras",
                description="Permite âncoras customizadas para categorias fixas.",
            ),
            "semantic_clusters": ProviderMetadata(
                label="Clusters Semânticos (TF-IDF)",
                description="Agrupa passagens similares sem embeddings.",
            ),
            "embedding_clusters": ProviderMetadata(
                label="Clusters por Embeddings",
                description="Exige sentence-transformers para clusters ricos.",
            ),
            "bertopic": ProviderMetadata(
                label="BERTopic",
                description="Modelo avançado baseado em embeddings + HDBSCAN.",
            ),
        },
    }


PROVIDER_METADATA: Dict[ProviderType, ProviderMetadataMap] = _build_map()


def get_provider_metadata(provider_type: ProviderType, name: str) -> Optional[ProviderMetadata]:
    """Return metadata if registered."""

    provider_map = PROVIDER_METADATA.get(provider_type, {})
    return provider_map.get(name)


__all__ = ["ProviderMetadata", "get_provider_metadata", "PROVIDER_METADATA"]
