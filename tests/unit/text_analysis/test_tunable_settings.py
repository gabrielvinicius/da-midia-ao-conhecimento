"""Parâmetros da análise, da revisão e do processamento vêm do ambiente.

Antes ficavam em constantes no código: mudar o tamanho do resumo ou a agenda
da revisão exigia um novo deploy.
"""
import datetime

import pytest

from src.text_analysis.domain.review import ReviewCard
from src.text_analysis.infrastructure.dependencies import pipeline_factory, providers

NOW = datetime.datetime(2026, 10, 18, 12, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture
def settings(monkeypatch):
    from src.shared.infrastructure.config.settings import settings

    def set_(**values):
        for name, value in values.items():
            monkeypatch.setattr(settings, name, value)

    return set_


def test_summary_chunks_grounding_and_chapters_come_from_the_environment(settings):
    settings(
        summary_percent=20,
        summary_min_words=50,
        summary_short_words=100,
        analysis_chunk_size=256,
        analysis_chunk_overlap=32,
        analysis_full_transcript_chars=9000,
        analysis_synthesis_block_chars=6000,
        grounding_threshold=0.7,
        chapters_min_recording_minutes=10,
        chapters_min_minutes=3,
        chapters_max=6,
        chapters_every_minutes=8,
    )

    config = providers.build_analysis_config()

    assert config.summary_length.target_words(10000) == 2000
    assert config.summary_length.target_words(100) == 50
    assert config.summary_length.short_words == 100
    assert (config.chunk_size, config.chunk_overlap) == (256, 32)
    assert (config.max_full_transcript_chars, config.synthesis_block_chars) == (9000, 6000)
    assert config.grounding_threshold == 0.7
    rules = config.chapter_rules
    assert (rules.min_recording_seconds, rules.min_chapter_seconds) == (600, 180)
    assert (rules.max_chapters, rules.seconds_per_chapter) == (6, 480)


def test_the_pipeline_steps_receive_the_configured_values(settings, monkeypatch):
    settings(summary_percent=7, chapters_max=4, analysis_full_transcript_chars=5000)
    monkeypatch.setattr(providers, "get_embedding_adapter", lambda _c: object())
    monkeypatch.setattr(providers, "get_text_generation_adapter", lambda _c: object())
    monkeypatch.setattr(providers, "get_sentiment_adapter", lambda _c: object())
    monkeypatch.setattr(providers, "get_topic_modeling_adapter", lambda _c: object())
    monkeypatch.setattr(providers, "get_chunker_adapter", lambda _c: object())

    steps = {
        s.name: s
        for s in pipeline_factory.build_analysis_pipeline(providers.build_analysis_config(), None).pipeline.steps
    }

    assert steps["synthesis"].length.percent == 7
    assert steps["chapters"].rules.max_chapters == 4
    assert steps["review_questions"].max_transcript_chars == 5000


def test_review_schedule_comes_from_the_environment(settings):
    from src.text_analysis.infrastructure.dependencies.builders import build_review_schedule

    settings(review_interval_days="0, 2, 5", review_mastered_box=2)
    schedule = build_review_schedule()

    card = ReviewCard().answered(True, NOW, schedule)
    assert card.due_at == NOW + datetime.timedelta(days=2)
    assert schedule.is_mastered(card)


def test_an_invalid_review_schedule_is_refused_at_startup(settings):
    from src.text_analysis.infrastructure.dependencies.builders import build_review_schedule

    settings(review_interval_days="0,1,3", review_mastered_box=5)
    with pytest.raises(ValueError, match="REVIEW_MASTERED_BOX"):
        build_review_schedule()


def test_frame_sampling_comes_from_the_processing_settings(monkeypatch):
    from src.media_processing.config.settings import processing_settings

    monkeypatch.setattr(processing_settings, "frame_every_seconds", 60)
    monkeypatch.setattr(processing_settings, "frames_min", 1)
    monkeypatch.setattr(processing_settings, "frames_max", 20)
    monkeypatch.setattr(processing_settings, "same_scene_similarity", 0.9)
    sampling = processing_settings.frame_sampling()

    assert len(sampling.timestamps(15 * 60)) == 15
    assert not sampling.is_same_scene("um homem fala ao microfone", "um homem fala")
