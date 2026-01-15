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
                        model_name = self.transformer_model_name or "Qwen/Qwen2.5-3B-Instruct"
                        if model_name.startswith("hf:"):
                            model_name = model_name[3:]
                        
                        logger.info(
                            "bertopic.init_llm_representation", 
                            model=model_name
                        )

                        # Pipeline de geração de texto
                        import torch
                        torch_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
                        
                        generator = pipeline(
                            "text-generation",
                            model=model_name,
                            device=device_idx,
                            torch_dtype=torch_dtype, # Use half precision
                            max_new_tokens=64  # Títulos curtos
                        )

                        # Prompt Otimizado (Compatible with Qwen/Llama/Mistral)
                        # Qwen 2.5 handles plain instructions well, but specific templates help.
                        base_instruction = (
                            "Tarefa: Identifique o tema unificador dos documentos abaixo.\n"
                            "Instrução: Gere APENAS um título curto (máx 6 palavras), direto e profissional em Português.\n"
                            "REGRAS: NÃO use aspas, NÃO explique, NÃO diga 'Aqui está o título', responda APENAS o texto do título.\n\n"
                            "Documentos:\n[DOCUMENTS]\n\n"
                            "Título:"
                        )
                        
                        # Simple Instruct format that works broadly
                        prompt = f"{base_instruction}"

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
                
                # Configure SentenceTransformer with E5 specific prompts
                emb_model_name = self.embedding_model_name or "intfloat/multilingual-e5-large"
                from sentence_transformers import SentenceTransformer
                import torch
                
                embedding_model = SentenceTransformer(
                    emb_model_name,
                    device=self.device,
                    model_kwargs={"torch_dtype": torch.float16}, # Save VRAM
                    prompts={"clustering": "Identify the topic or theme based on the text: "}
                )
                
                # IMPORTANT: KeyBERTInspired needs the embedding model to embed keywords
                representation_models["KeyBERT"] = KeyBERTInspired()

                self._model = BERTopic(
                    embedding_model=embedding_model,
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
                import torch
                
                if torch.cuda.is_available():
                    torch.cuda.empty_cache() # Free up space before heavy operation

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
                logger.info("bertopic.run_completed", 
                            topic_count=len(set(topics)), 
                            unique_topics=list(set(topics)),
                            info=info.to_dict() if hasattr(info, "to_dict") else str(info))
                
                topics_out: list[Topic] = []
                # Se apenas ruído foi encontrado, vamos tratar o ruído como um tópico geral
                # para não quebrar o pipeline de sumarização
                effective_topic_ids = set(topics)
                if len(effective_topic_ids) == 1 and -1 in effective_topic_ids:
                    logger.warning("bertopic.only_noise_found_mapping_to_general")
                    # Mapeia tudo para o tópico 0 temporariamente para o loop abaixo
                    topics = [0 for _ in topics]
                    effective_topic_ids = {0}

                for topic_id in sorted(list(effective_topic_ids)):
                    if topic_id == -1: continue # Skip outlier topic if desired

                    # Tenta obter o título do LLM, fallback para KeyBERT, fallback para palavras
                    topic_meta = model.get_topic(topic_id, full=True)
                    
                    # Prioridade: LLM -> KeyBERT -> Default
                    title = None
                    if "LLM" in topic_meta and topic_meta["LLM"]:
                         raw_llm_title = topic_meta["LLM"][0][0] # (word, score)
                         # Cleanup chatty LLM
                         title = self._clean_llm_title(raw_llm_title)
                    
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
                            diagnostics={"probabilities": probs.tolist() if hasattr(probs, "tolist") else probs},
                        )
                    )
                diagnostics = {
                    "topics": info.to_dict() if hasattr(info, "to_dict") else {}
                }
                return topics_out, diagnostics
            except Exception as exc:  # pragma: no cover
                logger.error("BERTopic run failed: %s", exc)
        return self._fallback(chunks)

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
