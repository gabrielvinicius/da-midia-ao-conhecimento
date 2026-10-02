"""Montagem única do pipeline de análise (usada pela API e pelos workers)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.application.pipeline.base import AnalysisPipeline
from src.text_analysis.application.pipeline.steps import (
    ChunkEmbeddingStep,
    ChunkingStep,
    GroundingCheckStep,
    KnowledgeIndexingStep,
    ReleaseMemoryStep,
    SentimentStep,
    SynthesisStep,
    TopicModelingStep,
    TopicTitleStep,
)


@dataclass
class PipelineComponents:
    pipeline: AnalysisPipeline
    embedding_adapter: Any
    text_generation_adapter: Any
    vector_repo: Any


def build_analysis_pipeline(config: AnalysisConfig, session: Any) -> PipelineComponents:
    """Compõe as etapas na ordem em que devem rodar.

    Primeiro as que usam modelos locais do worker (vetores, sentimento,
    temas), depois a devolução da memória da GPU e só então as que
    usam o modelo de linguagem no Ollama (títulos e síntese), que é
    descarregado ao fim da análise. Numa GPU de 12 GB os dois grupos não
    cabem juntos.

    Sentimento, temas (com seus títulos) e verificação de fidelidade são
    fatores opcionais (``config.factors``): desligado, o fator não entra na
    lista e o modelo dele nem é carregado. As demais etapas lidam com a
    falta do que ele produziria.
    """
    from src.text_analysis.infrastructure.adapters.gpu_memory_releaser import TorchCacheReleaser
    from src.text_analysis.infrastructure.dependencies.providers import (
        get_chunker_adapter,
        get_embedding_adapter,
        get_sentiment_adapter,
        get_text_generation_adapter,
        get_topic_modeling_adapter,
    )
    from src.text_analysis.infrastructure.repositories.vector_repository import (
        VectorRepository,
    )

    embedding_adapter = get_embedding_adapter(config)
    gen_adapter = get_text_generation_adapter(config)
    vector_repo = VectorRepository(session)

    factors = config.factors
    steps = [
        ChunkingStep(get_chunker_adapter(config), size=config.chunk_size, overlap=config.chunk_overlap),
        ChunkEmbeddingStep(embedding_adapter),
    ]
    if "sentiment" in factors:
        steps.append(SentimentStep(get_sentiment_adapter(config), language=config.language))
    if "topics" in factors:
        steps.append(TopicModelingStep(get_topic_modeling_adapter(config), embedding_adapter, language=config.language))
    steps += [KnowledgeIndexingStep(vector_repo), ReleaseMemoryStep([TorchCacheReleaser()])]
    if "topics" in factors:
        steps.append(TopicTitleStep(gen_adapter, language=config.language))
    steps.append(
        SynthesisStep(
            gen_adapter,
            language=config.language,
            max_full_transcript_chars=config.max_full_transcript_chars,
            block_chars=config.synthesis_block_chars,
        )
    )
    if "grounding" in factors:
        steps.append(GroundingCheckStep(embedding_adapter, threshold=config.grounding_threshold))

    pipeline = AnalysisPipeline(
        steps=steps,
        release_after_run=[gen_adapter],
    )
    return PipelineComponents(
        pipeline=pipeline,
        embedding_adapter=embedding_adapter,
        text_generation_adapter=gen_adapter,
        vector_repo=vector_repo,
    )
