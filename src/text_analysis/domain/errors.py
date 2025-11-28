"""Domain-level exceptions for text analysis."""


class DomainError(Exception):
    """Base class for domain errors."""


class EmptyTextError(DomainError):
    """Raised when text content is empty or only whitespace."""


class InvalidSegmentError(DomainError):
    """Raised when a provided segment payload is malformed."""

