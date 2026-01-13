"""BERTopic adapter with fallback heuristic."""

from __future__ import annotations

from collections import Counter

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.config.settings import settings
from src.text_analysis.application.ports.topic_modeling import TopicModelingPort
from src.text_analysis.domain import TextChunk, Topic

logger = get_logger(__name__)


class BERTopicAdapter(TopicModelingPort):
    def __init__(
        self,
        model_name: str,
        use_transformer_representation: bool = False,
        transformer_model_name: str | None = None,
        embedding_model_name: str | None = None,  # NEW
        device: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.use_transformer_representation = use_transformer_representation
        self.transformer_model_name = transformer_model_name
        self.embedding_model_name = embedding_model_name # NEW
        self.device = device or settings.resolved_device
        self._model = None
        self._initialized = False

    def _get_model(self):
        if not self._initialized:
            try:  # pragma: no cover
                from bertopic import BERTopic
                from bertopic.representation import KeyBERTInspired, TextGeneration

                # 1. Base Representation: KeyBERTInspired (Robust & Fast)
                # Melhora a qualidade das keywords focando na semântica, não apenas frequência
                representation_models = {
                    "KeyBERT": KeyBERTInspired()
                }

                # ... (Transformer Representation logic hidden for brevity) ...
                if self.use_transformer_representation:
                    try:
                        from transformers import pipeline

                        # Map 'cpu' or device ID
                        device_idx = -1 if self.device == "cpu" else 0
                        
                        # Strip routing prefix 'hf:' if present
                        model_name = self.transformer_model_name or "google/flan-t5-base"
                        if model_name.startswith("hf:"):
                            model_name = model_name[3:]
                        
                        logger.info(
                            "bertopic.init_llm_representation", 
                            model=model_name
                        )

                        # Pipeline de geração de texto
                        generator = pipeline(
                            "text2text-generation" if "t5" in model_name.lower() else "text-generation",
                            model=model_name,
                            device=device_idx,
                            max_new_tokens=32  # Títulos curtos
                        )

                        # Prompt Otimizado
                        prompt = (
                            "Analise os seguintes documentos que compartilham o mesmo tópico:\n"
                            "[DOCUMENTS]\n\n"
                            "Identifique o tema central unificador e gere um título curto, "
                            "descritivo e profissional em Português para este tópico. "
                            "Apenas o título, sem aspas ou explicações:"
                        )

                        representation_models["LLM"] = TextGeneration(
                            generator, 
                            prompt=prompt
                        )
                        
                    except Exception as rep_exc:  # pragma: no cover
                        logger.warning(
                            "bertopic.llm_representation_failed",
                            error=str(rep_exc)
                        )

                # Initialize BERTopic with Multi-Aspect Representation AND Embedding Model
                # Explicitly setting embedding_model avoids 'NoneType' error in KeyBERT
                # even when using pre-computed embeddings.
                self._model = BERTopic(
                    embedding_model=self.embedding_model_name or "sentence-transformers/all-MiniLM-L6-v2",
                    representation_model=representation_models,
                    verbose=True
                )
                
            except Exception as exc:
                logger.warning(
                    "BERTopic unavailable (%s). Using simple keywords fallback.", exc
                )
            self._initialized = True
        return self._model

    async def model_topics(
        self, chunks: list[TextChunk], embeddings: list[list[float]], language: str
    ) -> tuple[list[Topic], dict]:
        model = self._get_model()
        if model and embeddings:
            try:
                import numpy as np  # lazy import to avoid hard dep at import time

                docs = [chunk.text for chunk in chunks]
                np_embeddings = (
                    embeddings
                    if hasattr(embeddings, "shape")
                    else np.array(embeddings, dtype="float32")
                )
                
                # Executa fit_transform em thread separada para não bloquear o loop de eventos
                # pois BERTopic/UMAP/HDBSCAN são CPU-bound e pesados
                import asyncio
                from functools import partial
                
                # Wrapper para chamar fit_transform
                def _run_fit():
                    return model.fit_transform(docs, np_embeddings)

                topics, probs = await asyncio.to_thread(_run_fit)
                
                info = model.get_topic_info()
                
                topics_out: list[Topic] = []
                for topic_id in set(topics):
                    if topic_id == -1: continue # Skip outlier topic if desired, or keep as "Ruído"

                    # Tenta obter o título do LLM, fallback para KeyBERT, fallback para palavras
                    topic_meta = model.get_topic(topic_id, full=True)
                    
                    # Prioridade: LLM -> KeyBERT -> Default
                    title = None
                    if "LLM" in topic_meta and topic_meta["LLM"]:
                         title = topic_meta["LLM"][0][0] # (word, score)
                    
                    if not title and "KeyBERT" in topic_meta:
                         # KeyBERT retorna keywords, pegamos a top 1 como "tema" se não houver título
                         title = topic_meta["KeyBERT"][0][0].capitalize()

                    # Keywords vêm do KeyBERT se disponível (melhor qualidade)
                    keywords_source = topic_meta.get("KeyBERT", model.get_topic(topic_id))
                    words = [term for term, _ in keywords_source][:10]
                    
                    if not title:
                        title = words[0].capitalize() if words else "Tópico Desconhecido"

                    snippets = [
                        chunk.text for chunk, t in zip(chunks, topics) if t == topic_id
                    ]
                    topics_out.append(
                        Topic(
                            id=int(topic_id),
                            keywords=words,
                            snippets=snippets[:5],
                            title=title.strip(),
                            size=len(snippets),
                            diagnostics={"probabilities": probs},
                        )
                    )
                diagnostics = {
                    "topics": info.to_dict() if hasattr(info, "to_dict") else {}
                }
                return topics_out, diagnostics
            except Exception as exc:  # pragma: no cover
                logger.error("BERTopic run failed: %s", exc)
        return self._fallback(chunks)

    def _fallback(self, chunks: list[TextChunk]) -> tuple[list[Topic], dict]:
        text_all = " ".join(chunk.text for chunk in chunks)
        tokens = [t.lower() for t in text_all.split() if len(t) > 3]
        common = [word for word, _ in Counter(tokens).most_common(10)]
        topic = Topic(
            id=0,
            keywords=common or ["geral"],
            snippets=[chunk.text for chunk in chunks[:3]],
            title=common[0] if common else "Geral",
            size=len(chunks),
            diagnostics={"method": "fallback"},
        )
        return [topic], {"method": "fallback"}
