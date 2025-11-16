"""Mapping helpers for summary aggregates."""

from __future__ import annotations

from datetime import datetime, timezone

from src.text_analysis.summarization.domain.model import SummaryAggregate

from .summary_entity import SummaryEntity


def _to_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


class SummaryMapper:
    """Converts between ORM entities and domain aggregates."""

    def to_domain(
        self,
        entity: SummaryEntity,
        *,
        template: SummaryAggregate | None = None,
    ) -> SummaryAggregate:
        aggregate = SummaryAggregate(
            id=entity.id,
            transcription_id=entity.transcription_id,
            text=entity.text,
            status=entity.status,
            created_at=entity.created_at,
            processed_at=entity.processed_at,
            error_message=entity.error_message,
            provider=entity.provider,
        )

        if template is not None:
            aggregate = aggregate.update(
                strategy=template.strategy,
                bullet_points=template.bullet_points,
                key_topics=template.key_topics,
                confidence_score=template.confidence_score,
                processing_time=template.processing_time,
            )

        return aggregate

    def to_entity(self, aggregate: SummaryAggregate) -> SummaryEntity:
        return SummaryEntity(
            id=aggregate.id,
            transcription_id=aggregate.transcription_id,
            text=aggregate.text,
            status=aggregate.status,
            created_at=_to_naive(aggregate.created_at) or datetime.utcnow(),
            processed_at=_to_naive(aggregate.processed_at),
            error_message=aggregate.error_message,
            provider=aggregate.provider,
        )

    def apply_to_entity(self, entity: SummaryEntity, aggregate: SummaryAggregate) -> SummaryEntity:
        entity.transcription_id = aggregate.transcription_id
        entity.text = aggregate.text
        entity.status = aggregate.status
        entity.created_at = _to_naive(aggregate.created_at) or entity.created_at
        entity.processed_at = _to_naive(aggregate.processed_at)
        entity.error_message = aggregate.error_message
        entity.provider = aggregate.provider
        return entity

    def merge_transient_data(
        self,
        persisted: SummaryAggregate,
        template: SummaryAggregate | None,
    ) -> SummaryAggregate:
        if template is None:
            return persisted
        return persisted.update(
            strategy=template.strategy,
            bullet_points=template.bullet_points,
            key_topics=template.key_topics,
            confidence_score=template.confidence_score,
            processing_time=template.processing_time,
        )
