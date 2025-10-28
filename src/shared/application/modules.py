"""Typed registry of bootstrapped application modules."""
from dataclasses import dataclass

from src.shared.events.event_bus import EventBus
from src.auth.bootstrap import AuthModule
from src.monitoring.bootstrap import MonitoringModule
from src.media_management.bootstrap import MediaModule
from src.video_processing.bootstrap import VideoProcessingModule
from src.text_processing.bootstrap import TextProcessingModule
from src.transcription.bootstrap import TranscriptionModule
from src.notifications.bootstrap import NotificationModule
from src.summarization.bootstrap import SummarizationModule
from src.providers.bootstrap import ProvidersModule
from src.sentiment_analysis.bootstrap import SentimentAnalysisModule
from src.topic_modeling.bootstrap import TopicModelingModule
from src.admin.bootstrap import AdminModule


@dataclass
class ModulesRegistry:
    auth: AuthModule
    monitoring: MonitoringModule
    media_management: MediaModule
    transcription: TranscriptionModule
    notifications: NotificationModule
    video_processing: VideoProcessingModule
    text_processing: TextProcessingModule
    summarization: SummarizationModule
    providers: ProvidersModule
    sentiment_analysis: SentimentAnalysisModule
    topic_modeling: TopicModelingModule
    admin: AdminModule
    event_bus: EventBus
