# src/shared/events/event_bus_config.py
from celery import Celery
import redis.asyncio as aioredis
from opentelemetry.instrumentation.celery import CeleryInstrumentor

from src.shared.config.broker_settings import BrokerSettings


class EventBusConfiguration:
    """
    Handles the configuration and instantiation of broker clients like Celery and Redis.
    """
    
    @staticmethod
    def create_celery_app() -> Celery:
        """Creates and configures a Celery application instance."""
        settings = BrokerSettings()
        celery = Celery(__name__, broker=settings.redis_url)
        celery.conf.task_serializer = 'json'
        celery.conf.result_serializer = 'json'
        celery.conf.accept_content = ['json']
        celery.autodiscover_tasks([
            "src.transcription.tasks",
            "src.summarization.tasks",
            "src.notifications.tasks",
            "src.sentiment_analysis.tasks",
            "src.topic_modeling.tasks",
            "src.video_processing.tasks",
            "src.text_processing.tasks",
        ])
        
        # Instrument Celery with OpenTelemetry
        CeleryInstrumentor().instrument()
        return celery

    @staticmethod
    def create_redis_client() -> aioredis.Redis:
        """Creates and configures an asynchronous Redis client."""
        settings = BrokerSettings()
        return aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )

# Export configured instances for easy import
celery_app = EventBusConfiguration.create_celery_app()
redis_client = EventBusConfiguration.create_redis_client()
