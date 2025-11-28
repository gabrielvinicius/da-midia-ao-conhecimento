"""Shared constants for integration events and task routing."""

# Task Names (Routing Keys)
TASK_MEDIA_TRANSCRIPTION = "media_processing.transcription"
TASK_MEDIA_VIDEO_PROCESSING = "media_processing.video"
TASK_TEXT_ANALYSIS_ANALYZE = "text_analysis.analyze"
TASK_TEXT_ANALYSIS_SUMMARIZE = "text_analysis.summarize"
TASK_TEXT_ANALYSIS_SENTIMENT = "text_analysis.sentiment"
TASK_TEXT_ANALYSIS_TOPIC_MODELING = "text_analysis.topic_modeling"

# Event Names (for future Event Bus usage)
EVENT_MEDIA_UPLOADED = "media.uploaded"
EVENT_TRANSCRIPTION_COMPLETED = "media.transcription.completed"
EVENT_ANALYSIS_COMPLETED = "media.analysis.completed"
