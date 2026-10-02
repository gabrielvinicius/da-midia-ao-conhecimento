"""Configuration objects for application layer."""

from __future__ import annotations

from dataclasses import dataclass, field

# Fatores opcionais da análise. Trechos, vetores, indexação e resumo sempre
# rodam: são a base da busca e da página da mídia.
OPTIONAL_FACTORS = frozenset({"sentiment", "topics", "grounding"})


@dataclass(slots=True)
class AnalysisConfig:
    language: str = "pt"
    chunk_size: int = 512
    chunk_overlap: int = 64
    sentiment_model: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    # multilingual-e5-small gera vetores de 384 dimensões, compatíveis com a
    # coluna knowledge_chunks.embedding (Vector(384)).
    embedding_model: str = "intfloat/multilingual-e5-small"
    topic_model: str = "bertopic"  # use "tfidf" para fallback leve sem deps pesadas
    # Nome do modelo servido pelo Ollama (ex.: "qwen3.5:9b").
    # A montagem do módulo (build_analysis_config) usa o valor das configurações.
    llm_model: str = "qwen3.5:9b"
    # Transcrições até este tamanho vão inteiras à síntese (~12 mil tokens,
    # dentro da janela de 16k do Ollama); acima, a síntese resume blocos de
    # synthesis_block_chars e une os resumos parciais.
    max_full_transcript_chars: int = 36000
    synthesis_block_chars: int = 36000
    # Similaridade mínima (cosseno, multilingual-e5) entre uma frase do resumo
    # e algum trecho da transcrição para a frase contar como apoiada.
    grounding_threshold: float = 0.80
    # Fatores ligados (ANALYSIS_FACTORS); desligar um tira o modelo dele da
    # análise sem alterar as demais etapas.
    factors: frozenset = field(default_factory=lambda: OPTIONAL_FACTORS)
