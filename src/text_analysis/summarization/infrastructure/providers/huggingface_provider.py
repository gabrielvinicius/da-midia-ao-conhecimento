# src/summarization/infrastructure/providers/huggingface_provider.py
"""HuggingFace summarization provider - OCP and SRP compliance.
"""
import asyncio
from threading import Lock
from typing import Any, Dict, Optional

import torch
from src.text_analysis.summarization.infrastructure.providers.base_provider import (
    BaseSummaryProvider,
)
from transformers import AutoTokenizer, pipeline


class HuggingFaceConfiguration:
    """Configuration for HuggingFace summarization - SRP compliance."""

    def __init__(
        self,
        model_name: str = "google-t5/t5-base",
        max_input_length: int = 512,
        max_output_length: int = 64,
        min_output_length: int = 16,
        device: str = "auto"
    ):
        self.model_name = model_name
        self.max_input_length = max_input_length
        self.max_output_length = max_output_length
        self.min_output_length = min_output_length
        self.device = device

    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "model_name": self.model_name,
            "max_input_length": self.max_input_length,
            "max_output_length": self.max_output_length,
            "min_output_length": self.min_output_length,
            "device": self.device
        }

    def validate_config(self) -> bool:
        """Validate configuration."""
        return (
            bool(self.model_name) and
            self.max_input_length > 0 and
            self.max_output_length > 0 and
            self.min_output_length > 0 and
            self.min_output_length <= self.max_output_length
        )

    def get_max_input_length(self) -> int:
        """Get maximum input text length."""
        return self.max_input_length

    def get_max_output_length(self) -> int:
        """Get maximum output summary length."""
        return self.max_output_length


class HuggingFaceSummaryProvider(BaseSummaryProvider):
    """HuggingFace summarization provider.
    Follows OCP - can be extended without modification.
    """

    def __init__(self, config: HuggingFaceConfiguration):
        super().__init__(config)
        self._config = config
        self._lock = Lock()

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "huggingface"

    def _initialize_provider(self) -> None:
        """Initialize HuggingFace components."""
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self._config.model_name)

            # Determine device
            if self._config.device == "auto":
                device = -1  # CPU by default for HuggingFace pipeline
                if torch.cuda.is_available():
                    device = 0
            else:
                device = -1 if self._config.device == "cpu" else 0

            self._summarizer = pipeline(
                "summarization",
                model=self._config.model_name,
                tokenizer=self._tokenizer,
                framework="pt",
                device=device
            )

            self._device = self._summarizer.device
            print(f"HuggingFace provider initialized on device: {self._device}")

        except Exception as e:
            raise SummaryProviderError(f"Failed to initialize HuggingFace provider: {e}") from e

    async def _do_summarize(self, text: str) -> str:
        """Actual summarization implementation."""
        if self._supports_chunking() and len(text) > self._config.get_max_input_length():
            return await self._summarize_chunked(text)
        else:
            return await self._summarize_single(text)

    async def _summarize_single(self, text: str) -> str:
        """Summarize single text chunk."""
        with self._lock:
            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: self._summarizer(
                        text,
                        max_length=self._config.max_output_length,
                        min_length=self._config.min_output_length,
                        do_sample=False,
                        num_beams=4,
                        truncation=True,
                        no_repeat_ngram_size=3
                    )[0]['summary_text']
                )
                return result
            except Exception as e:
                raise SummaryProviderError(f"Summarization failed: {e}") from e

    async def _summarize_chunked(self, text: str) -> str:
        """Summarize text in chunks."""
        chunks = self._get_text_chunks(text)
        summaries = []

        for chunk in chunks:
            if chunk.strip():
                summary = await self._summarize_single(chunk)
                if summary.strip():
                    summaries.append(summary)

        # Combine chunk summaries
        combined = " ".join(summaries)

        # If combined summary is still too long, summarize it again
        if len(combined) > self._config.get_max_input_length():
            combined = await self._summarize_single(combined)

        return combined

    def _supports_chunking(self) -> bool:
        """Whether provider supports text chunking."""
        return True

    def _supports_custom_length(self) -> bool:
        """Whether provider supports custom summary length."""
        return True

    async def _preprocess_text(self, text: str) -> str:
        """Preprocess text for HuggingFace."""
        # Clean and normalize text
        text = super()._preprocess_text(text)

        # Remove excessive whitespace
        text = " ".join(text.split())

        return text

    async def _post_summarize(self, text: str, summary: str) -> None:
        """Clean up after summarization."""
        # Clear GPU cache if using CUDA
        if hasattr(self._device, 'type') and self._device.type == 'cuda':
            torch.cuda.empty_cache()
        elif hasattr(self._device, 'type') and self._device.type == 'xpu':
            torch.xpu.empty_cache()

    async def _get_provider_specific_capabilities(self) -> Dict[str, Any]:
        """Get HuggingFace-specific capabilities."""
        return {
            "model_name": self._config.model_name,
            "device": str(self._device),
            "supports_beam_search": True,
            "supports_no_repeat_ngram": True,
            "tokenizer_vocab_size": len(self._tokenizer) if self._tokenizer else 0
        }

    def _get_text_chunks(self, text: str, chunk_size: Optional[int] = None) -> list[str]:
        """Split text using tokenizer for more accurate chunking."""
        if chunk_size is None:
            chunk_size = self._config.get_max_input_length()

        # Use tokenizer for more accurate chunking
        tokens = self._tokenizer.tokenize(text)
        chunks = []

        for i in range(0, len(tokens), chunk_size):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self._tokenizer.convert_tokens_to_string(chunk_tokens)
            chunks.append(chunk_text)

        return chunks
