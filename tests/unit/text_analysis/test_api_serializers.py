"""Unit tests for the API-facing DTO mappers in text analysis modules."""

from datetime import datetime, timezone
from uuid import uuid4

from src.text_analysis.sentiment_analysis.api.schemas import (
    SentimentAnalysisResponse,
)
from src.text_analysis.sentiment_analysis.domain.sentiment_analysis import (
    SentimentAnalysis,
)
from src.text_analysis.summarization.api.schemas import SummaryResponse
from src.text_analysis.summarization.domain.model.summary_aggregate import (
    SummaryAggregate,
)
from src.text_analysis.topic_modeling.api.schemas import TopicModelingResponse
from src.text_analysis.topic_modeling.domain.analysis import TopicModelingStatus
from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult


def test_summary_response_from_domain_normalises_collections() -> None:
    media_id = uuid4()
    summary = SummaryAggregate.create(media_id=media_id, provider="builtin")
    summary = summary.mark_as_completed("Concise summary")
    summary = summary.update(
        strategy="textrank",
        bullet_points=("Point A", "Point B"),
        key_topics=("AI", "ML"),
        confidence_score=0.92,
        processing_time=3.4,
    )

    dto = SummaryResponse.from_domain(summary)

    assert dto.id == str(summary.id)
    assert dto.media_id == str(media_id)
    assert dto.status == summary.status
    assert dto.strategy == "textrank"
    assert dto.bullet_points == ["Point A", "Point B"]
    assert dto.key_topics == ["AI", "ML"]
    assert dto.confidence_score == 0.92
    assert dto.processing_time == 3.4


def test_sentiment_analysis_response_flattens_domain_payload() -> None:
    analysis = SentimentAnalysis(
        id=str(uuid4()),
        media_id=str(uuid4()),
        transcription_id=str(uuid4()),
        overall_sentiment="POSITIVE",
        sentiment_score=0.78,
        confidence=0.81,
        emotions={"joy": 0.6, "trust": 0.4},
        sentence_sentiments=[{"text": "Great", "score": 0.9}],
        provider="huggingface",
        model="distilbert-base-uncased",
        processing_time=2.1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    dto = SentimentAnalysisResponse.from_domain(analysis)

    assert dto.id == analysis.id
    assert dto.label == "POSITIVE"
    assert dto.score == analysis.sentiment_score
    assert dto.confidence == analysis.confidence
    assert dto.full_result["emotions"] == analysis.emotions
    assert dto.full_result["sentence_sentiments"] == analysis.sentence_sentiments
    assert dto.full_result["provider"] == analysis.provider
    assert dto.full_result["model"] == analysis.model


def test_topic_modeling_response_converts_topics_to_strings() -> None:
    media_id = uuid4()
    result = TopicModelingResult(
        id=uuid4(),
        media_id=media_id,
        topics=[
            {"name": "Tech", "keywords": ["ai", "ml"]},
            "General insights",
        ],
        status=TopicModelingStatus.COMPLETED,
        provider="bertopic",
    )
    result.created_at = datetime.now(timezone.utc)
    result.processed_at = datetime.now(timezone.utc)

    dto = TopicModelingResponse.from_domain(result)

    assert dto.id == str(result.id)
    assert dto.media_id == str(media_id)
    assert dto.status == TopicModelingStatus.COMPLETED
    assert dto.provider == "bertopic"
    assert dto.topics[0] == "Tech: ai, ml"
    assert "General insights" in dto.topics
    assert dto.raw_topics and dto.raw_topics[0]["name"] == "Tech"
