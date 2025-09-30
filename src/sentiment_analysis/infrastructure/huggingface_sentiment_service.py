# src/sentiment_analysis/infrastructure/huggingface_sentiment_service.py
from transformers import pipeline
from typing import Dict, Any
import structlog

from .interfaces import ISentimentAnalysisService
from .dependencies import register_sentiment_analysis

logger = structlog.get_logger(__name__)

@register_sentiment_analysis("huggingface")
class HuggingFaceSentimentAnalysisService(ISentimentAnalysisService):
    """Implementation of the sentiment analysis service using a Hugging Face model."""

    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        try:
            logger.info("sentiment_analysis.service.init", model=model_name)
            self.pipeline = pipeline("sentiment-analysis", model=model_name)
            logger.info("sentiment_analysis.service.loaded", model=model_name)
        except Exception as e:
            logger.error("sentiment_analysis.service.init_failed", error=str(e))
            raise

    @property
    def provider_name(self) -> str:
        return "huggingface"

    def analyze(self, text: str) -> Dict[str, Any]:
        """Performs sentiment analysis on the given text."""
        if not text or not text.strip():
            return {"label": "NEUTRAL", "score": 1.0, "detail": "Input text was empty."}

        try:
            result = self.pipeline(text, truncation=True, max_length=512)
            return result[0]
        except Exception as e:
            logger.error("sentiment_analysis.process.failed", error=str(e))
            return {"label": "ERROR", "score": 0.0, "detail": str(e)}
