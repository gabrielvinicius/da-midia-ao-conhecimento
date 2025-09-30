# src/sentiment_analysis/infrastructure/huggingface_sentiment_service.py
from transformers import pipeline
from typing import Dict, Any
import structlog

from .interfaces import ISentimentAnalysisService

logger = structlog.get_logger(__name__)

class HuggingFaceSentimentAnalysisService(ISentimentAnalysisService):
    """Implementation of the sentiment analysis service using a Hugging Face model."""

    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        try:
            logger.info("sentiment_analysis.service.init", model=model_name)
            # Initialize the pipeline. This will download the model on the first run.
            self.pipeline = pipeline("sentiment-analysis", model=model_name)
            logger.info("sentiment_analysis.service.loaded", model=model_name)
        except Exception as e:
            logger.error("sentiment_analysis.service.init_failed", error=str(e))
            raise

    def analyze(self, text: str) -> Dict[str, Any]:
        """Performs sentiment analysis on the given text."""
        if not text or not text.strip():
            return {"label": "NEUTRAL", "score": 1.0, "detail": "Input text was empty."}

        try:
            # The pipeline returns a list of results; we only need the first one.
            result = self.pipeline(text, truncation=True, max_length=512)
            return result[0]
        except Exception as e:
            logger.error("sentiment_analysis.process.failed", error=str(e))
            # Return a neutral/error state instead of raising an exception
            return {"label": "ERROR", "score": 0.0, "detail": str(e)}
