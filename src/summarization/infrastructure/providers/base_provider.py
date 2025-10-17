# src/summarization/infrastructure/providers/base_provider.py
"""
Base implementation for summarization providers - Template Method pattern.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time

from src.summarization.domain.interfaces import SummaryProvider, SummaryConfiguration


class SummaryProviderError(Exception):
    """Base exception for summarization provider errors."""
    pass


class BaseSummaryProvider(SummaryProvider):
    """
    Base summarization provider implementing common functionality.
    Follows Template Method pattern and OCP.
    """
    
    def __init__(self, config: SummaryConfiguration):
        self._config = config
        self._validate_configuration()
        self._initialize_provider()
    
    def _validate_configuration(self) -> None:
        """Validate provider configuration."""
        if not self._config.validate_config():
            raise SummaryProviderError("Invalid summarization configuration")
    
    @abstractmethod
    def _initialize_provider(self) -> None:
        """Initialize provider-specific components."""
        pass
    
    async def summarize(self, text: str) -> str:
        """Template method for text summarization."""
        try:
            # Pre-summarization hook
            await self._pre_summarize(text)
            
            # Input validation
            self._validate_input(text)
            
            # Text preprocessing
            processed_text = await self._preprocess_text(text)
            
            # Actual summarization (implemented by subclasses)
            summary = await self._do_summarize(processed_text)
            
            # Post-processing
            final_summary = await self._postprocess_summary(summary)
            
            # Post-summarization hook
            await self._post_summarize(text, final_summary)
            
            return final_summary
            
        except Exception as e:
            await self._handle_summarization_error(text, e)
            raise SummaryProviderError(f"Summarization failed") from e
    
    def _validate_input(self, text: str) -> None:
        """Validate input text."""
        if not text or not text.strip():
            raise SummaryProviderError("Input text is empty or invalid")
        
        max_length = self._config.get_max_input_length()
        if len(text) > max_length:
            raise SummaryProviderError(f"Input text too long: {len(text)} > {max_length}")
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities."""
        return {
            "provider_name": self.provider_name,
            "max_input_length": self._config.get_max_input_length(),
            "max_output_length": self._config.get_max_output_length(),
            "supports_chunking": self._supports_chunking(),
            "supports_custom_length": self._supports_custom_length(),
            **await self._get_provider_specific_capabilities()
        }
    
    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def _do_summarize(self, text: str) -> str:
        """Actual summarization implementation."""
        pass
    
    @abstractmethod
    def _supports_chunking(self) -> bool:
        """Whether provider supports text chunking."""
        pass
    
    @abstractmethod
    def _supports_custom_length(self) -> bool:
        """Whether provider supports custom summary length."""
        pass
    
    # Hook methods (can be overridden by subclasses)
    async def _pre_summarize(self, text: str) -> None:
        """Hook called before summarization."""
        pass
    
    async def _post_summarize(self, text: str, summary: str) -> None:
        """Hook called after successful summarization."""
        pass
    
    async def _preprocess_text(self, text: str) -> str:
        """Preprocess input text."""
        # Default implementation: basic cleaning
        return text.strip()
    
    async def _postprocess_summary(self, summary: str) -> str:
        """Postprocess generated summary."""
        # Default implementation: basic cleaning
        cleaned = summary.strip()
        
        # Ensure summary doesn't exceed max length
        max_length = self._config.get_max_output_length()
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rsplit(' ', 1)[0] + '...'
        
        return cleaned
    
    async def _handle_summarization_error(self, text: str, error: Exception) -> None:
        """Handle summarization errors."""
        pass
    
    async def _get_provider_specific_capabilities(self) -> Dict[str, Any]:
        """Get provider-specific capabilities."""
        return {}
    
    def _get_text_chunks(self, text: str, chunk_size: Optional[int] = None) -> list[str]:
        """Split text into chunks for processing."""
        if chunk_size is None:
            chunk_size = self._config.get_max_input_length()
        
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks