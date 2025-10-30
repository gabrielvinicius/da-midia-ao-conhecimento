# src/topic_modeling/domain/analysis.py
"""Domain enumerations for the topic modeling module."""

from enum import Enum


class TopicModelingStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


__all__ = ["TopicModelingStatus"]
