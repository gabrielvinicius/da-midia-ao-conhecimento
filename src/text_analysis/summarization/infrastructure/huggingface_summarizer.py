import asyncio
from threading import Lock
from typing import Any, Dict, Optional

import torch
from transformers import AutoTokenizer, pipeline


class HuggingFaceSummarizer:
    def __init__(self, model_name="google-t5/t5-base"):
        """Initializes the summarizer with automatic device detection.
        """
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        self.model_max_length = getattr(self.tokenizer, 'model_max_length', 1024)
        self.max_input_length = min(self.model_max_length, 512)
        self.max_summary_length = 64
        self.min_summary_length = 16

        self.summarizer = pipeline(
            "summarization",
            model=model_name,
            tokenizer=self.tokenizer,
            framework="pt",
            device=-1
        )

        self.device = self.summarizer.device
        print(f"HuggingFaceSummarizer initialized. Automatically selected device: {self.device}")

        self.lock = Lock()

    @property
    def provider_name(self) -> str:
        return "huggingface"

    def empty_device_cache(self):
        """Frees unused device memory, if applicable."""
        if self.device.type == 'cuda':
            torch.cuda.empty_cache()
        elif self.device.type == 'xpu':
            torch.xpu.empty_cache()

    def split_text_into_chunks(self, text: str) -> list[str]:
        """Splits the text into token-based chunks"""
        if not text.strip():
            return []

        tokens = self.tokenizer.tokenize(text)
        chunks = [
            tokens[i:i + self.max_input_length]
            for i in range(0, len(tokens), self.max_input_length)
        ]

        return [
            self.tokenizer.convert_tokens_to_string(chunk)
            for chunk in chunks
        ]

    async def summarize(self, text_content: str, options: Optional[Dict[str, Any]] = None) -> str: # Atualizar assinatura
        """Processes the text in chunks and returns the concatenated summary"""
        if not text_content.strip():
            return ""

        self.empty_device_cache()

        chunks = self.split_text_into_chunks(text_content)
        summaries = []

        for chunk in chunks:
            summary = await self._summarize_chunk(chunk, options)
            summaries.append(summary)

        self.empty_device_cache()

        return " ".join(summaries)

    async def _summarize_chunk(self, chunk: str, options: Optional[Dict[str, Any]] = None) -> str: # Atualizar assinatura
        """Processes an individual chunk with robust error handling"""
        with self.lock:
            loop = asyncio.get_event_loop()
            try:
                # Usar opções se fornecidas, caso contrário, usar defaults
                max_length = options.get("max_length", self.max_summary_length) if options else self.max_summary_length
                min_length = options.get("min_length", self.min_summary_length) if options else self.min_summary_length

                return await loop.run_in_executor(
                    None,
                    lambda: self.summarizer(
                        chunk,
                        max_length=max_length,
                        min_length=min_length,
                        do_sample=options.get("do_sample", False) if options else False,
                        num_beams=options.get("num_beams", 4) if options else 4,
                        truncation=options.get("truncation", True) if options else True,
                        no_repeat_ngram_size=options.get("no_repeat_ngram_size", 3) if options else 3
                    )[0]['summary_text']
                )
            except Exception as e:
                print(f"Error summarizing chunk: {str(e)}")
                return ""
