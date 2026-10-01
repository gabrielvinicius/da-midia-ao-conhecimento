"""BERTopic adapter with fallback heuristic."""

from __future__ import annotations

from typing import Any

from collections import Counter

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.config.settings import settings
from src.text_analysis.application.ports.topic_modeling import TopicModelingPort
from src.text_analysis.domain import TextChunk, Topic
from src.text_analysis.infrastructure.adapters.stopwords import (
    PORTUGUESE_STOPWORDS,
    stop_words_for,
)

logger = get_logger(__name__)

# Abaixo disso o UMAP do BERTopic falha (poucos pontos para a redução de
# dimensão) e agrupar não faz sentido: o texto vira um único tema.
MIN_CHUNKS_FOR_CLUSTERING = 8


def representative_snippets(chunks, members: list[int], embeddings, limit: int = 5) -> list[str]:
    """Os trechos mais próximos do centro do tema, na ordem da gravação.

    Antes eram os cinco primeiros trechos do tema, o que mostrava só o começo
    do assunto no apêndice de conferência e nos títulos.
    """
    import numpy as np

    if len(members) <= limit:
        return [chunks[i].text for i in members]
    vectors = np.asarray([embeddings[i] for i in members], dtype="float32")
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True).clip(min=1e-12)
    centroid = vectors.mean(axis=0)
    closest = np.argsort(-(vectors @ centroid))[:limit]
    return [chunks[members[i]].text for i in sorted(closest)]


class BERTopicAdapter(TopicModelingPort):
    def __init__(
        self,
        model_name: str,
        use_transformer_representation: bool = False,
        transformer_model_name: str | None = None,
        embedding_model_name: str | None = None,
        embedding_model_inst: Any | None = None,  # NEW: Injected Instance
        device: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.use_transformer_representation = use_transformer_representation
        self.transformer_model_name = transformer_model_name
        self.embedding_model_name = embedding_model_name
        self.embedding_model_inst = embedding_model_inst # NEW
        self.device = device or settings.resolved_device
        self._embedding_model = None
        self._representation_models = None
        self._dependencies_loaded = False

    def _ensure_dependencies(self):
        """Carrega os modelos pesados (LLM, Embeddings) apenas uma vez."""
        if not self._dependencies_loaded:
            try:  # pragma: no cover
                from bertopic.representation import KeyBERTInspired, TextGeneration

                # 1. Base Representation: KeyBERTInspired
                self._representation_models = {
                    "KeyBERT": KeyBERTInspired()
                }

                # ... (Transformer logic omitted for brevity, assumes existing) ...
                if self.use_transformer_representation:
                    # (LLM loading logic remains same)
                    try:
                        from transformers import pipeline
                        # ...
                        # (This part is fine, LLM is loaded only here or in TextGen adapter - separate concerns)
                        # Actually, we should check if we can share LLM too, but let's focus on Embedding first.
                        pass
                    except: pass
                    
                    # Re-implementing the LLM loading part briefly to ensure context consistency in replacement
                    try:
                        from transformers import pipeline
                        device_idx = -1 if self.device == "cpu" else 0
                        model_name = self.transformer_model_name or "Qwen/Qwen2.5-3B-Instruct"
                        if model_name.startswith("hf:"): model_name = model_name[3:]
                        import torch
                        torch_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
                        generator = pipeline("text-generation", model=model_name, device=device_idx, torch_dtype=torch_dtype, max_new_tokens=64)
                        base_instruction = "Tarefa: Identifique o tema unificador dos documentos abaixo.\nInstrução: Gere APENAS um título curto (máx 6 palavras), direto e profissional em Português.\nREGRAS: NÃO use aspas, NÃO explique, NÃO diga 'Aqui está o título', responda APENAS o texto do título.\n\nDocumentos:\n[DOCUMENTS]\n\nTítulo:"
                        self._representation_models["LLM"] = TextGeneration(generator, prompt=base_instruction)
                    except Exception as rep_exc:
                        logger.warning("bertopic.llm_representation_failed", error=str(rep_exc))

                # Initialize Embedding Model
                # Optimization: Use injected instance if available to save VRAM
                if self.embedding_model_inst:
                    logger.info("bertopic.using_shared_embedding_model")
                    self._embedding_model = self.embedding_model_inst
                else:
                    logger.info("bertopic.loading_new_embedding_model")
                    emb_model_name = self.embedding_model_name or "intfloat/multilingual-e5-large"
                    from sentence_transformers import SentenceTransformer
                    import torch
                    self._embedding_model = SentenceTransformer(
                        emb_model_name,
                        device=self.device,
                        model_kwargs={"torch_dtype": torch.float16},
                        prompts={"clustering": "Identify the topic or theme based on the text: "}
                    )
                
                # Update KeyBERT with the correct embedding model
                self._representation_models["KeyBERT"] = KeyBERTInspired()
                
            except Exception as exc:
                logger.warning("BERTopic dependencies unavailable (%s).", exc)
                raise exc
            self._dependencies_loaded = True

    def _calculate_dynamic_params(self, doc_count: int) -> dict:
        """
        Calcula parâmetros do BERTopic baseado no tamanho do conteúdo.
        Objetivo: Garantir granularidade (3-4 tópicos min) mesmo em vídeos curtos.
        """
        # Regra: ~2.5% das sentenças (Mais granularidade/Tópicos). 
        # Ex: 100 frases -> min_size=2 ou 3. 
        target_size = int(doc_count * 0.025)
        # Mantemos o piso em 2 para máxima granularidade (micro-tópicos), teto em 15.
        min_topic_size = max(2, min(15, target_size))
        
        logger.info("bertopic.dynamic_params", doc_count=doc_count, min_topic_size=min_topic_size)
        return {"min_topic_size": min_topic_size}

    async def model_topics(
        self, chunks: list[TextChunk], embeddings: list[list[float]], language: str
    ) -> tuple[list[Topic], dict]:
        if len(chunks) < MIN_CHUNKS_FOR_CLUSTERING:
            logger.info("bertopic.too_few_chunks", chunk_count=len(chunks))
            return self._fallback(chunks, language)

        # Garante que deps pesadas estão na memória
        self._ensure_dependencies()
        
        if self._embedding_model:
            try:
                from bertopic import BERTopic
                import numpy as np
                import torch
                
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

                docs = [chunk.text for chunk in chunks]
                
                # Configuração Dinâmica por Execução
                params = self._calculate_dynamic_params(len(docs))
                
                # Instancia BERTopic leve (modelos pesados injetados)
                from sklearn.feature_extraction.text import CountVectorizer

                topic_model = BERTopic(
                    embedding_model=self._embedding_model,
                    representation_model=self._representation_models,
                    # Sem palavras vazias, as palavras-chave em português
                    # seriam "de", "que", "para".
                    vectorizer_model=CountVectorizer(stop_words=stop_words_for(language)),
                    min_topic_size=params["min_topic_size"],
                    verbose=True,
                    # calculate_probabilities=True # Opcional, consome mais RAM
                )

                np_embeddings = (
                    embeddings
                    if hasattr(embeddings, "shape")
                    else np.array(embeddings, dtype="float32")
                )
                
                import asyncio
                
                def _run_fit():
                    return topic_model.fit_transform(docs, np_embeddings)

                topics, probs = await asyncio.to_thread(_run_fit)
                
                # O resto do código usa 'topic_model' em vez de self._model
                info = topic_model.get_topic_info()
                logger.info("bertopic.run_completed", 
                            topic_count=len(set(topics)), 
                            unique_topics=list(set(topics)),
                            info=info.to_dict() if hasattr(info, "to_dict") else str(info))
                
                topics_out: list[Topic] = []
                effective_topic_ids = set(topics)
                
                # Se só achou ruído (-1) ou 1 tópico, força o mapeamento
                if len(effective_topic_ids) <= 1:
                    logger.warning("bertopic.low_diversity_found", topics=list(effective_topic_ids))
                    # Se só tem -1, vira 0. Se só tem 0, fica 0.
                    topics = [0 if t == -1 else t for t in topics]
                    effective_topic_ids = {0}

                for topic_id in sorted(list(effective_topic_ids)):
                    if topic_id == -1: continue

                    topic_meta = topic_model.get_topic(topic_id, full=True)
                    
                    title = None
                    if "LLM" in topic_meta and topic_meta["LLM"]:
                         raw_llm_title = topic_meta["LLM"][0][0]
                         title = self._clean_llm_title(raw_llm_title)
                    
                    if not title and "KeyBERT" in topic_meta:
                         title = topic_meta["KeyBERT"][0][0].capitalize()

                    keywords_source = topic_meta.get("KeyBERT", topic_model.get_topic(topic_id))
                    words = [term for term, _ in keywords_source][:10]
                    
                    if not title:
                        title = words[0].capitalize() if words else "Tópico Desconhecido"

                    members = [i for i, t in enumerate(topics) if t == topic_id]
                    snippets = representative_snippets(chunks, members, np_embeddings)
                    
                    # Cálculo de diagnósticos seguro
                    topic_probs = []
                    if probs is not None:
                        if hasattr(probs, "tolist"):
                             # probs pode ser lista de listas ou lista simples dependendo do HDBSCAN
                             pass 

                    topics_out.append(
                        Topic(
                            id=int(topic_id),
                            keywords=words,
                            snippets=snippets,
                            title=title.strip(),
                            size=len(members),
                            diagnostics={"score": 1.0} # Simplificado
                        )
                    )
                diagnostics = {
                    "topics": info.to_dict() if hasattr(info, "to_dict") else {}
                }
                return topics_out, diagnostics
            except Exception as exc:  # pragma: no cover
                logger.error("BERTopic run failed: %s", exc, exc_info=True)
        return self._fallback(chunks, language)

    def _clean_llm_title(self, text: str) -> str:
        """Limpa títulos gerados por LLMs que tendem a ser 'conversas'."""
        if not text: return ""
        # Remove prefixos comuns
        prefixes = [
            "Título:", "Title:", "Tema central:", "Tema:", "O tema central é:",
            "Aqui está o título:", "O título curto e profissional é:",
            "O título sugerido é:", "Resumo:", "[RESPOSTA CORRETA]", "[RESPOSTA]"
        ]
        cleaned = text.strip()
        
        # Pega apenas a primeira linha não vazia (evita explicações)
        lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
        if lines:
            cleaned = lines[0]
            
        for p in prefixes:
            if cleaned.lower().startswith(p.lower()):
                cleaned = cleaned[len(p):].strip()
        
        # Remove aspas
        cleaned = cleaned.replace('"', '').replace('"', '').replace("'", "")
        
        # Se for longo demais, trunca na primeira frase ou vírgula
        if len(cleaned) > 100:
            import re
            parts = re.split(r'[:\.\n]', cleaned)
            cleaned = parts[0].strip()
            
        return cleaned.strip().capitalize()

    def _fallback(
        self, chunks: list[TextChunk], language: str | None = None
    ) -> tuple[list[Topic], dict]:
        """Um único tema com as palavras mais frequentes do texto.

        Usado em textos curtos e quando o BERTopic falha.
        """
        stop = set(stop_words_for(language) or PORTUGUESE_STOPWORDS)
        text_all = " ".join(chunk.text for chunk in chunks)
        tokens = [
            t.strip(".,;:!?()[]\"'«»“”").lower() for t in text_all.split()
        ]
        tokens = [t for t in tokens if len(t) > 3 and t not in stop and not t.isdigit()]
        common = [word for word, _ in Counter(tokens).most_common(10)]
        topic = Topic(
            id=0,
            keywords=common or ["geral"],
            snippets=[chunk.text for chunk in chunks[:3]],
            title=" e ".join(common[:2]).capitalize() if common else "Geral",
            size=len(chunks),
            diagnostics={"method": "fallback"},
        )
        return [topic], {"method": "fallback"}
