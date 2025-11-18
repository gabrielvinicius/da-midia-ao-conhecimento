"""Topic modeling providers and registry.

Este módulo expõe dois providers:
- ``SklearnLDATopicModeler``: usa scikit-learn (CountVectorizer + LDA).
- ``KeywordFrequencyTopicModeler``: fallback rápido baseado em frequência de palavras.

Ambos compartilham a mesma interface síncrona/assíncrona para que o serviço
``TopicModelingService`` consiga selecionar o provider via nome.
"""

from __future__ import annotations

import asyncio
import importlib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import structlog

from src.providers.domain.interfaces import (
    IProviderRegistry,
    ProviderCapability,
    ProviderStatus,
    ProviderType,
)
from src.providers.domain.provider import Provider

logger = structlog.get_logger(__name__)

try:  # scikit-learn é opcional, mas preferido quando disponível
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.feature_extraction.text import CountVectorizer
except ModuleNotFoundError:  # pragma: no cover - ambiente sem sklearn
    LatentDirichletAllocation = None
    CountVectorizer = None

try:
    from bertopic import BERTopic
except ModuleNotFoundError:  # pragma: no cover
    BERTopic = None

ProviderFactory = Callable[..., "BaseTopicModeler"]
REGISTERED_FACTORIES: Dict[str, ProviderFactory] = {}


def register_topic_modeler(name: str) -> Callable[[ProviderFactory], ProviderFactory]:
    """Decorator para registrar providers sem tocar no container principal."""

    def decorator(factory: ProviderFactory) -> ProviderFactory:
        REGISTERED_FACTORIES[name] = factory
        return factory

    return decorator


def load_topic_modeler_plugins(module_paths: List[str]) -> None:
    """Importa módulos extras para que eles se registrem via decorator."""

    for module_path in module_paths:
        module_path = module_path.strip()
        if not module_path:
            continue
        try:
            importlib.import_module(module_path)
        except Exception as exc:  # pragma: no cover - defensivo
            logger.error("topic_modeler.plugin_load_failed", module=module_path, error=str(exc))


def create_registry(
    *,
    enabled: List[str],
    default_provider: str,
    plugin_modules: Optional[List[str]] = None,
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> "TopicModelerRegistry":
    if plugin_modules:
        load_topic_modeler_plugins(plugin_modules)
    return TopicModelerRegistry.from_specs(
        enabled=enabled,
        default_provider=default_provider,
        overrides=overrides,
    )


def register_providers_in_registry(
    topic_registry: "TopicModelerRegistry",
    provider_registry: IProviderRegistry | None,
) -> None:
    """Sync topic modelers with the shared provider registry."""

    if provider_registry is None:
        return

    capability_map = {
        "sklearn_lda": [ProviderCapability.BATCH_PROCESSING, ProviderCapability.MULTI_LANGUAGE],
        "bertopic": [
            ProviderCapability.BATCH_PROCESSING,
            ProviderCapability.MULTI_LANGUAGE,
            ProviderCapability.CUSTOM_MODELS,
        ],
        "keyword_frequency": [ProviderCapability.BATCH_PROCESSING],
    }

    for name, modeler in topic_registry.providers.items():
        capabilities = capability_map.get(name, [ProviderCapability.BATCH_PROCESSING])
        provider = Provider(
            name=name,
            provider_type=ProviderType.TOPIC_MODELING,
            status=ProviderStatus.ACTIVE,
            capabilities=capabilities,
            version=getattr(modeler, "provider_version", "1.0.0"),
            configuration={
                "default": topic_registry.default_provider == name,
            },
        )
        try:
            provider_registry.register_provider(provider)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning(
                "topic_modeler.provider_registry_register_failed",
                provider=name,
                error=str(exc),
            )


class BaseTopicModeler:
    """Classe base com contratos síncrono/assíncrono."""

    provider_name: str = "base"

    async def model_topics(
        self,
        text_content: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.model_topics_sync,
            text_content,
            language,
            options,
        )

    def model_topics_sync(
        self,
        text_content: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    @staticmethod
    def _build_payload(
        provider: str,
        language: str,
        text_content: str,
        raw_topics: List[Dict[str, Any]],
        *,
        model_name: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "provider": provider,
            "model_name": model_name,
            "language": language,
            "topics": raw_topics,
            "num_topics": len(raw_topics),
            "text_length": len(text_content),
            "options": options or {},
        }


class SklearnLDATopicModeler(BaseTopicModeler):
    """Provider baseado em scikit-learn LDA."""

    provider_name = "sklearn_lda"

    def __init__(
        self,
        *,
        max_features: int = 2000,
        default_topics: int = 5,
        default_words: int = 6,
        random_state: int = 42,
    ) -> None:
        if CountVectorizer is None or LatentDirichletAllocation is None:
            raise RuntimeError(
                "scikit-learn não está instalado; instale 'scikit-learn' para usar o provider sklearn_lda"
            )
        self.max_features = max_features
        self.default_topics = default_topics
        self.default_words = default_words
        self.random_state = random_state

    def model_topics_sync(
        self,
        text_content: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cleaned = text_content.strip()
        if not cleaned:
            return self._build_payload(self.provider_name, language, text_content, [], model_name="sklearn.LDA")

        documents = self._split_documents(cleaned)
        num_topics = self._resolve_num_topics(len(documents), options)
        num_words = self._resolve_num_words(options)

        stop_words = self._resolve_stop_words(language)
        vectorizer = CountVectorizer(
            stop_words=stop_words,
            max_features=self.max_features,
            max_df=0.95,
            min_df=2,
            ngram_range=(1, 2),
        )

        matrix = vectorizer.fit_transform(documents)
        lda = LatentDirichletAllocation(
            n_components=num_topics,
            learning_method="batch",
            random_state=self.random_state,
            max_iter=10,
        )
        lda.fit(matrix)

        feature_names = vectorizer.get_feature_names_out()
        topics: List[Dict[str, Any]] = []
        for idx, topic_row in enumerate(lda.components_):
            top_indices = topic_row.argsort()[:-num_words - 1:-1]
            keywords = [feature_names[i] for i in top_indices]
            weights = topic_row[top_indices]
            topics.append(
                {
                    "id": idx,
                    "name": f"Topic {idx + 1}",
                    "keywords": keywords,
                    "scores": [float(w) for w in weights],
                }
            )

        logger.info(
            "topic_modeler.sklearn.completed",
            provider=self.provider_name,
            num_topics=len(topics),
            language=language,
        )
        return self._build_payload(
            self.provider_name,
            language,
            text_content,
            topics,
            model_name="sklearn.LDA",
            options=options,
        )

    @staticmethod
    def _split_documents(text: str) -> List[str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) >= 3:
            return paragraphs

        sentences = re.split(r"(?<=[.!?])\s+", text)
        docs = [s.strip() for s in sentences if len(s.strip()) > 40]
        return docs or [text]

    def _resolve_num_topics(self, doc_count: int, options: Optional[Dict[str, Any]]) -> int:
        requested = int(options.get("num_topics")) if options and options.get("num_topics") else None
        if requested:
            return max(2, min(10, requested))
        base = self.default_topics
        if doc_count >= 8:
            base = min(10, base + 2)
        return base

    def _resolve_num_words(self, options: Optional[Dict[str, Any]]) -> int:
        requested = int(options.get("num_words_per_topic")) if options and options.get("num_words_per_topic") else None
        if requested:
            return max(3, min(15, requested))
        return self.default_words

    @staticmethod
    def _resolve_stop_words(language: str) -> Optional[str]:
        mapping = {
            "en": "english",
            "pt": "portuguese",
            "es": "spanish",
            "fr": "french",
        }
        return mapping.get(language.lower(), "english")


class BertopicModeler(BaseTopicModeler):
    """Provider baseado na biblioteca BERTopic."""

    provider_name = "bertopic"

    def __init__(
        self,
        *,
        embedding_model: Optional[str] = None,
        min_topic_size: int = 10,
        verbose: bool = False,
    ) -> None:
        if BERTopic is None:
            raise RuntimeError(
                "bertopic não está instalado. Adicione 'bertopic' às dependências para usar este provider."
            )
        self.embedding_model = embedding_model
        self.min_topic_size = min_topic_size
        self.verbose = verbose

    def model_topics_sync(
        self,
        text_content: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cleaned = text_content.strip()
        if not cleaned:
            return self._build_payload(self.provider_name, language, text_content, [], model_name="BERTopic")

        documents = self._split_documents(cleaned)
        num_words = self._resolve_num_words(options)
        try:
            topic_model = BERTopic(
                language=language,
                embedding_model=self.embedding_model,
                min_topic_size=self.min_topic_size,
                verbose=self.verbose,
            )
            topics, _ = topic_model.fit_transform(documents)
            topic_dict = topic_model.get_topics()
        except Exception as exc:  # pragma: no cover - dependência externa
            logger.error("topic_modeler.bertopic.failed", error=str(exc))
            raise

        extracted: List[Dict[str, Any]] = []
        seen: set[int] = set()
        for topic_id in topics:
            if topic_id < 0 or topic_id in seen:
                continue
            seen.add(topic_id)
            words = topic_dict.get(topic_id) or []
            if not words:
                continue
            chunk = words[:num_words]
            extracted.append(
                {
                    "id": int(topic_id),
                    "name": f"Topic {topic_id}",
                    "keywords": [word for word, _ in chunk],
                    "scores": [float(score) for _, score in chunk],
                }
            )

        # Ordena por ID e corta caso usuário solicite menos tópicos
        extracted.sort(key=lambda item: item["id"])
        max_topics = self._resolve_num_topics(options)
        if max_topics:
            extracted = extracted[:max_topics]

        logger.info(
            "topic_modeler.bertopic.completed",
            provider=self.provider_name,
            num_topics=len(extracted),
            language=language,
        )
        return self._build_payload(
            self.provider_name,
            language,
            text_content,
            extracted,
            model_name="BERTopic",
            options=options,
        )

    def _split_documents(self, text: str) -> List[str]:
        docs = [seg.strip() for seg in re.split(r"\n+", text) if len(seg.strip()) > 40]
        if not docs:
            docs = [text]
        return docs

    @staticmethod
    def _resolve_num_topics(options: Optional[Dict[str, Any]]) -> Optional[int]:
        if not options or "num_topics" not in options:
            return None
        try:
            return max(1, int(options["num_topics"]))
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return None

    @staticmethod
    def _resolve_num_words(options: Optional[Dict[str, Any]]) -> int:
        if not options:
            return 6
        try:
            return max(3, min(15, int(options.get("num_words_per_topic", 6))))
        except (TypeError, ValueError):  # pragma: no cover
            return 6


class KeywordFrequencyTopicModeler(BaseTopicModeler):
    """Fallback provider baseado em frequência de palavras (sem sklearn)."""

    provider_name = "keyword_frequency"

    def __init__(self, *, default_topics: int = 3, default_words: int = 6) -> None:
        self.default_topics = default_topics
        self.default_words = default_words

    def model_topics_sync(
        self,
        text_content: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cleaned = text_content.strip().lower()
        if not cleaned:
            return self._build_payload(self.provider_name, language, text_content, [], model_name="keyword-frequency")

        tokens = self._tokenize(cleaned)
        stop_words = self._stop_words(language)
        filtered = [token for token in tokens if token not in stop_words and len(token) > 3]
        if not filtered:
            filtered = tokens

        num_topics = max(1, min(8, options.get("num_topics"))) if options and options.get("num_topics") else self.default_topics
        num_words = max(3, min(10, options.get("num_words_per_topic"))) if options and options.get("num_words_per_topic") else self.default_words

        counts = Counter(filtered)
        most_common = counts.most_common(num_topics * num_words)

        topics: List[Dict[str, Any]] = []
        for idx in range(num_topics):
            slice_start = idx * num_words
            chunk = most_common[slice_start:slice_start + num_words]
            if not chunk:
                break
            keywords = [word for word, _ in chunk]
            scores = [float(score) for _, score in chunk]
            topics.append(
                {
                    "id": idx,
                    "name": f"Topic {idx + 1}",
                    "keywords": keywords,
                    "scores": scores,
                }
            )

        if not topics:
            topics = [
                {
                    "id": 0,
                    "name": "Topic 1",
                    "keywords": [word for word, _ in most_common[:num_words]],
                    "scores": [float(score) for _, score in most_common[:num_words]],
                }
            ]

        logger.info(
            "topic_modeler.keyword_frequency.completed",
            provider=self.provider_name,
            num_topics=len(topics),
            language=language,
        )
        return self._build_payload(
            self.provider_name,
            language,
            text_content,
            topics,
            model_name="keyword-frequency",
            options=options,
        )

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", text)

    @staticmethod
    def _stop_words(language: str) -> set[str]:
        base = {
            "en": {
                "the",
                "and",
                "that",
                "with",
                "from",
                "this",
                "have",
                "were",
                "their",
                "your",
                "about",
                "into",
            },
            "pt": {
                "que",
                "para",
                "como",
                "mais",
                "este",
                "essa",
                "com",
                "sobre",
                "entre",
            },
            "es": {"que", "para", "como", "pero", "este", "esta", "con"},
        }
        return base.get(language.lower(), base["en"])


@register_topic_modeler("sklearn_lda")
def _build_sklearn_provider(**kwargs: Any) -> BaseTopicModeler:
    return SklearnLDATopicModeler(**kwargs)


@register_topic_modeler("keyword_frequency")
def _build_keyword_provider(**kwargs: Any) -> BaseTopicModeler:
    return KeywordFrequencyTopicModeler(**kwargs)


if BERTopic is not None:  # pragma: no cover - dependência opcional

    @register_topic_modeler("bertopic")
    def _build_bertopic_provider(**kwargs: Any) -> BaseTopicModeler:
        return BertopicModeler(**kwargs)


@dataclass
class TopicModelerRegistry:
    """Registro simples de providers disponíveis."""

    providers: Dict[str, BaseTopicModeler] = field(default_factory=dict)
    default_provider: str = "sklearn_lda"

    def get(self, provider: Optional[str]) -> BaseTopicModeler:
        return self.providers[self.resolve_name(provider)]

    def available(self) -> List[str]:
        return sorted(self.providers.keys())

    def resolve_name(self, provider: Optional[str]) -> str:
        if provider and provider in self.providers:
            return provider
        if provider and provider.startswith("bertopic") and "bertopic" in self.providers:
            return "bertopic"
        if provider and provider.startswith("keyword") and "keyword_frequency" in self.providers:
            return "keyword_frequency"
        if provider and provider.startswith("sklearn") and "sklearn_lda" in self.providers:
            return "sklearn_lda"
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
    ) -> "TopicModelerRegistry":
        overrides = overrides or {}
        instances: Dict[str, BaseTopicModeler] = {}
        for name in enabled:
            factory = REGISTERED_FACTORIES.get(name)
            if factory is None:
                raise ValueError(f"Topic modeling provider '{name}' is not registered. Import plugin or add it via settings.")
            kwargs = overrides.get(name, {}) or {}
            instances[name] = factory(**kwargs)
        if not instances:
            raise ValueError("No topic modeling providers available; check configuration.")
        resolved_default = default_provider if default_provider in instances else next(iter(instances))
        return cls(providers=instances, default_provider=resolved_default)
