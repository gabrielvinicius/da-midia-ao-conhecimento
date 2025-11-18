"""Pluggable sentiment analyzer providers."""

from __future__ import annotations

import asyncio
import math
import re
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    from transformers import pipeline
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pipeline = None

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ModuleNotFoundError:  # pragma: no cover
    SentimentIntensityAnalyzer = None

ProviderFactory = Callable[..., "BaseSentimentProvider"]
REGISTERED_FACTORIES: Dict[str, ProviderFactory] = {}


def register_sentiment_provider(name: str) -> Callable[[ProviderFactory], ProviderFactory]:
    """Decorator used by providers (built-in or plugin) to register themselves."""

    def decorator(factory: ProviderFactory) -> ProviderFactory:
        REGISTERED_FACTORIES[name] = factory
        return factory

    return decorator


def load_sentiment_provider_plugins(module_paths: List[str]) -> None:
    """Import arbitrary modules to register extra providers."""

    for module_path in module_paths:
        module_path = module_path.strip()
        if not module_path:
            continue
        try:
            __import__(module_path)
        except Exception as exc:  # pragma: no cover - defensivo
            logger.error("sentiment_provider.plugin_load_failed", module=module_path, error=str(exc))


class BaseSentimentProvider:
    provider_name = "base"

    async def analyze(
        self,
        *,
        text: str,
        language: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.analyze_sync,
            text=text,
            language=language,
            model=model,
            options=options,
        )

    def analyze_sync(
        self,
        *,
        text: str,
        language: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError


@register_sentiment_provider("transformers")
class TransformersSentimentProvider(BaseSentimentProvider):
    provider_name = "transformers"

    def __init__(
        self,
        *,
        model_name: str = "distilbert-base-uncased-finetuned-sst-2-english",
        device: Optional[int] = None,
        max_chars_per_segment: int = 512,
    ) -> None:
        if pipeline is None:
            raise RuntimeError(
                "transformers não está instalado. Adicione 'transformers' para usar este provider."
            )
        self.model_name = model_name
        self.device = device
        self.max_chars_per_segment = max_chars_per_segment
        self._pipeline = None
        self._lock = threading.Lock()

    def _ensure_pipeline(self):
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    self._pipeline = pipeline(
                        "sentiment-analysis",
                        model=self.model_name,
                        device=self.device,
                    )
        return self._pipeline

    def analyze_sync(
        self,
        *,
        text: str,
        language: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        classifier = self._ensure_pipeline()
        segments = self._segment_text(text)
        outputs = classifier(segments)

        signed_scores: List[float] = []
        sentence_payloads: List[Dict[str, Any]] = []
        for segment, output in zip(segments, outputs):
            label = output["label"].lower()
            score = float(output["score"])
            signed = score if "pos" in label else -score
            signed_scores.append(signed)
            sentence_payloads.append(
                {
                    "text": segment,
                    "label": "positive" if signed > 0 else "negative",
                    "score": score,
                }
            )

        avg_score = sum(signed_scores) / max(len(signed_scores), 1)
        sentiment = self._label_from_score(avg_score)
        confidence = max(abs(avg_score), max((abs(s) for s in signed_scores), default=0.0))

        return {
            "overall_sentiment": sentiment,
            "sentiment_score": avg_score,
            "confidence": float(min(1.0, 0.5 + confidence)),
            "emotions": {
                "joy": max(avg_score, 0.0),
                "frustration": max(-avg_score, 0.0),
            },
            "sentence_sentiments": sentence_payloads,
            "language": language or "en",
            "provider": self.provider_name,
            "model": model or self.model_name,
        }

    def _segment_text(self, text: str) -> List[str]:
        cleaned = text.strip()
        if not cleaned:
            return [""]
        if len(cleaned) <= self.max_chars_per_segment:
            return [cleaned]
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        segments: List[str] = []
        buffer = ""
        for sentence in sentences:
            if not sentence:
                continue
            candidate = f"{buffer} {sentence}".strip()
            if len(candidate) <= self.max_chars_per_segment:
                buffer = candidate
            else:
                if buffer:
                    segments.append(buffer)
                buffer = sentence.strip()
        if buffer:
            segments.append(buffer)
        return segments or [cleaned[: self.max_chars_per_segment]]

    @staticmethod
    def _label_from_score(score: float) -> str:
        if score > 0.1:
            return "positive"
        if score < -0.1:
            return "negative"
        return "neutral"


@register_sentiment_provider("vader")
class VaderSentimentProvider(BaseSentimentProvider):
    provider_name = "vader"

    def __init__(self) -> None:
        if SentimentIntensityAnalyzer is None:
            raise RuntimeError(
                "vaderSentiment não está instalado. Adicione 'vaderSentiment' para usar este provider."
            )
        self._vader = SentimentIntensityAnalyzer()

    def analyze_sync(
        self,
        *,
        text: str,
        language: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip()) if text.strip() else [""]
        sentence_payloads: List[Dict[str, Any]] = []
        signed_scores: List[float] = []
        for sentence in sentences:
            if not sentence:
                continue
            scores = self._vader.polarity_scores(sentence)
            compound = float(scores["compound"])
            signed_scores.append(compound)
            sentence_payloads.append(
                {
                    "text": sentence,
                    "label": self._label_from_score(compound),
                    "score": abs(compound),
                }
            )

        avg_score = sum(signed_scores) / max(len(signed_scores), 1)
        sentiment = self._label_from_score(avg_score)
        confidence = min(1.0, 0.5 + abs(avg_score))

        return {
            "overall_sentiment": sentiment,
            "sentiment_score": avg_score,
            "confidence": confidence,
            "emotions": {
                "joy": max(avg_score, 0.0),
                "frustration": max(-avg_score, 0.0),
            },
            "sentence_sentiments": sentence_payloads,
            "language": language or "en",
            "provider": self.provider_name,
            "model": model,
        }

    @staticmethod
    def _label_from_score(score: float) -> str:
        if score > 0.05:
            return "positive"
        if score < -0.05:
            return "negative"
        return "neutral"


@register_sentiment_provider("simple_keyword")
class SimpleKeywordSentimentProvider(BaseSentimentProvider):
    provider_name = "simple_keyword"

    POSITIVE_WORDS = {
        "good",
        "great",
        "excellent",
        "love",
        "happy",
        "amazing",
        "wonderful",
        "recommend",
        "enjoy",
        "satisfied",
    }
    NEGATIVE_WORDS = {
        "bad",
        "terrible",
        "awful",
        "hate",
        "sad",
        "horrible",
        "angry",
        "disappointed",
        "frustrated",
        "poor",
    }

    def analyze_sync(
        self,
        *,
        text: str,
        language: Optional[str] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        tokens = re.findall(r"\w+", text.lower())
        counter = Counter(tokens)
        pos_hits = sum(counter[word] for word in self.POSITIVE_WORDS)
        neg_hits = sum(counter[word] for word in self.NEGATIVE_WORDS)
        total = max(pos_hits + neg_hits, 1)
        score = (pos_hits - neg_hits) / total
        sentiment = self._label_from_score(score)
        return {
            "overall_sentiment": sentiment,
            "sentiment_score": score,
            "confidence": min(1.0, 0.5 + abs(score)),
            "emotions": {
                "joy": max(score, 0.0),
                "frustration": max(-score, 0.0),
            },
            "sentence_sentiments": [],
            "language": language or "en",
            "provider": self.provider_name,
            "model": model,
        }

    @staticmethod
    def _label_from_score(score: float) -> str:
        if score > 0.1:
            return "positive"
        if score < -0.1:
            return "negative"
        return "neutral"


@dataclass
class SentimentAnalyzerRegistry:
    providers: Dict[str, BaseSentimentProvider] = field(default_factory=dict)
    default_provider: str = "transformers"

    def get(self, provider: Optional[str]) -> BaseSentimentProvider:
        resolved = self.resolve_name(provider)
        return self.providers[resolved]

    def resolve_name(self, provider: Optional[str]) -> str:
        if provider and provider in self.providers:
            return provider
        if provider and provider.startswith("vader") and "vader" in self.providers:
            return "vader"
        if provider and provider.startswith("transformer") and "transformers" in self.providers:
            return "transformers"
        if provider and provider.startswith("simple") and "simple_keyword" in self.providers:
            return "simple_keyword"
        if self.default_provider in self.providers:
            return self.default_provider
        return next(iter(self.providers))

    @classmethod
    def from_specs(
        cls,
        *,
        enabled: List[str],
        default_provider: str,
        overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> "SentimentAnalyzerRegistry":
        overrides = overrides or {}
        instances: Dict[str, BaseSentimentProvider] = {}
        for name in enabled:
            factory = REGISTERED_FACTORIES.get(name)
            if factory is None:
                raise ValueError(f"Sentiment provider '{name}' is not registered. Importe o plugin ou ajuste a configuração.")
            kwargs = overrides.get(name, {}) or {}
            instances[name] = factory(**kwargs)
        if not instances:
            raise ValueError("Nenhum provider de sentimento disponível.")
        resolved_default = default_provider if default_provider in instances else next(iter(instances))
        return cls(providers=instances, default_provider=resolved_default)


def create_registry(
    *,
    enabled: List[str],
    default_provider: str,
    plugin_modules: Optional[List[str]] = None,
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> SentimentAnalyzerRegistry:
    if plugin_modules:
        load_sentiment_provider_plugins(plugin_modules)
    return SentimentAnalyzerRegistry.from_specs(
        enabled=enabled,
        default_provider=default_provider,
        overrides=overrides,
    )


__all__ = [
    "BaseSentimentProvider",
    "TransformersSentimentProvider",
    "VaderSentimentProvider",
    "SimpleKeywordSentimentProvider",
    "SentimentAnalyzerRegistry",
    "register_sentiment_provider",
    "create_registry",
    "load_sentiment_provider_plugins",
]
