from enum import Enum


class MediaType(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"


class MediaStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
