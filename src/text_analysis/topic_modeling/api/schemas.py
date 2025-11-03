"""Topic Modeling API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.shared.api.unified_schemas import BaseResponseSchema
from src.text_analysis.topic_modeling.domain.analysis import TopicModelingStatus
from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult


class TopicModelingResponse(BaseModel):
    """Flattened response consumed by the frontend."""

    id: str
    media_id: str
    status: TopicModelingStatus
    provider: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    raw_topics: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def _coerce_topics(topics_payload: Any) -> tuple[List[str], Optional[List[Dict[str, Any]]]]:
        if topics_payload is None:
            return [], None

        if isinstance(topics_payload, dict):
            candidate = topics_payload.get("topics")
            if isinstance(candidate, list):
                return TopicModelingResponse._coerce_topics(candidate)
            if isinstance(topics_payload, list):  # defensive - unlikely branch
                return TopicModelingResponse._coerce_topics(list(topics_payload))
            return [], None

        if not isinstance(topics_payload, list):
            return [str(topics_payload)], None

        serialisable: List[Dict[str, Any]] = []
        readable: List[str] = []
        for index, item in enumerate(topics_payload, start=1):
            if isinstance(item, dict):
                serialisable.append(item)
                label = item.get("name") or item.get("label") or f"Topic #{index}"
                keywords = item.get("keywords") or item.get("terms") or []
                if isinstance(keywords, dict):
                    keywords = keywords.values()
                if isinstance(keywords, (list, tuple, set)):
                    keywords_str = ", ".join(str(keyword) for keyword in keywords)
                else:
                    keywords_str = str(keywords)
                readable.append(f"{label}: {keywords_str}".strip())
            else:
                readable.append(str(item))

        return readable, serialisable or None

    @classmethod
    def from_domain(cls, result: TopicModelingResult) -> "TopicModelingResponse":
        topics, raw_topics = cls._coerce_topics(result.topics)

        return cls(
            id=str(result.id),
            media_id=str(result.media_id),
            status=result.status,
            provider=getattr(result, "provider", None),
            topics=topics,
            created_at=result.created_at,
            processed_at=getattr(result, "processed_at", None),
            error_message=getattr(result, "error_message", None),
            raw_topics=raw_topics,
        )


class TopicModelingAck(BaseModel):
    """Acknowledgement returned when topic modeling is scheduled."""

    media_id: Optional[str] = None
    provider: str
    language: str
    status: Literal["PROCESSING"] = "PROCESSING"
    task_id: Optional[str] = None


class TopicModelingAcceptedResponse(BaseResponseSchema):
    """Envelope emitted when a topic modeling request is accepted."""

    analysis: TopicModelingAck


__all__ = [
    "TopicModelingAck",
    "TopicModelingAcceptedResponse",
    "TopicModelingResponse",
]
