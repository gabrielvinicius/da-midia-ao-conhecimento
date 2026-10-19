"""Configuration objects for application layer."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.text_analysis.domain.chapters import ChapterRules
from src.text_analysis.domain.content_profile import SummaryLength

# Fatores opcionais da análise. Trechos, vetores, indexação e resumo sempre
# rodam: são a base da busca e da página da mídia.
OPTIONAL_FACTORS = frozenset({"sentiment", "topics", "grounding", "chapters", "questions"})


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
    # A montagem do módulo (build_analysis_config) preenche esta configuração
    # com os valores do ambiente; os padrões aqui servem aos testes.
    llm_model: str = "qwen3.5:9b"
    # Transcrições até este tamanho vão inteiras à síntese e às perguntas
    # (ANALYSIS_FULL_TRANSCRIPT_CHARS; ver SynthesisStep).
    max_full_transcript_chars: int = 18000
    synthesis_block_chars: int = 18000
    # GROUNDING_THRESHOLD: similaridade mínima para uma frase contar como apoiada.
    grounding_threshold: float = 0.80
    # Fatores ligados (ANALYSIS_FACTORS); desligar um tira o modelo dele da
    # análise sem alterar as demais etapas.
    factors: frozenset = field(default_factory=lambda: OPTIONAL_FACTORS)
    # Tamanho do resumo (SUMMARY_*) e limites dos capítulos (CHAPTERS_*).
    summary_length: SummaryLength = field(default_factory=SummaryLength)
    chapter_rules: ChapterRules = field(default_factory=ChapterRules)
