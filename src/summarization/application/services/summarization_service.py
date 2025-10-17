# src/summarization/application/services/summarization_service.py
from src.shared.resilience.circuit_breaker import get_circuit_breaker
from src.summarization.infrastructure.interfaces import ISummarizer


class SummarizationService:
    """
    A service layer that wraps the summarizer interface, adding resilience patterns.
    """
    def __init__(self, summarizer_provider: ISummarizer):
        self.provider = summarizer_provider

    async def summarize(self, text_content: str) -> str:
        """
        Summarizes text using the configured provider with a circuit breaker.
        """
        if not text_content:
            raise ValueError("Text content is empty, cannot summarize.")
            
        breaker = get_circuit_breaker(f"summarization_{self.provider.provider_name}")
        
        summary_text = await breaker.call_async(
            self.provider.summarize, 
            text_content
        )
        return summary_text
