"""Montagem única do pipeline de análise (usada pela API e pelos workers)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.application.pipeline.base import AnalysisPipeline
from src.text_analysis.application.pipeline.steps import (
    ChunkingStep,
    GroundingCheckStep,
    KnowledgeIndexingStep,
    ReleaseMemoryStep,
    SentimentStep,
    SynthesisStep,
    TopicModelingStep,
    TopicTitleStep,
    VisualInsightStep,
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
    temas, visão), depois a devolução da memória da GPU e só então as que
    usam o modelo de linguagem no Ollama (títulos e síntese), que é
    descarregado ao fim da análise. Numa GPU de 12 GB os dois grupos não
    cabem juntos.
    """
    from src.media_processing.infrastructure.adapters.video.ffmpeg_frame_extractor import (
        FFmpegFrameExtractor,
    )
    from src.media_processing.infrastructure.dependencies.providers import (
        get_visual_analyzer,
    )
    from src.shared.infrastructure.config.settings import settings
    from src.storage.infrastructure.dependencies import StorageServiceFactory
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

    pipeline = AnalysisPipeline(
        steps=[
            ChunkingStep(get_chunker_adapter(config), size=config.chunk_size, overlap=config.chunk_overlap),
            SentimentStep(get_sentiment_adapter(config), language=config.language),
            TopicModelingStep(get_topic_modeling_adapter(config), embedding_adapter, language=config.language),
            KnowledgeIndexingStep(vector_repo),
            VisualInsightStep(
                get_visual_analyzer(settings.visual_provider),
                FFmpegFrameExtractor(),
                StorageServiceFactory(),
            ),
            ReleaseMemoryStep([TorchCacheReleaser()]),
            TopicTitleStep(gen_adapter, language=config.language),
            SynthesisStep(
                gen_adapter,
                language=config.language,
                max_full_transcript_chars=config.max_full_transcript_chars,
                block_chars=config.synthesis_block_chars,
            ),
            GroundingCheckStep(embedding_adapter, threshold=config.grounding_threshold),
        ],
        release_after_run=[gen_adapter],
    )
    return PipelineComponents(
        pipeline=pipeline,
        embedding_adapter=embedding_adapter,
        text_generation_adapter=gen_adapter,
        vector_repo=vector_repo,
    )
