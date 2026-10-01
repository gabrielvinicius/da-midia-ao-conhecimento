"""Configuration objects for application layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisConfig:
    language: str = "pt"
    chunk_size: int = 512
    chunk_overlap: int = 64
    sentiment_model: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    # multilingual-e5-small gera vetores de 384 dimensões, compatíveis com a
    # coluna knowledge_chunks.embedding (Vector(384)).
    embedding_model: str = "intfloat/multilingual-e5-small"
    topic_model: str = "bertopic"  # use "tfidf" para fallback leve sem deps pesadas
    # Nome de modelo Ollama (ex.: "qwen3.5:9b"); prefixo "hf:" usa Transformers.
    # A montagem do módulo (build_analysis_config) usa o valor das configurações.
    llm_model: str = "qwen3.5:9b"
    # Carregar um segundo LLM dentro do BERTopic não cabe em GPUs de 12 GB;
    # os títulos dos temas são gerados pelo LLM principal no TopicTitleStep.
    use_transformer_topic_representation: bool = False
    transformer_representation_model: str = "hf:Qwen/Qwen2.5-3B-Instruct"
    # Transcrições até este tamanho vão inteiras à síntese (~12 mil tokens,
    # dentro da janela de 16k do Ollama); acima, a síntese resume blocos de
    # synthesis_block_chars e une os resumos parciais.
    max_full_transcript_chars: int = 36000
    synthesis_block_chars: int = 20000
    # Similaridade mínima (cosseno, multilingual-e5) entre uma frase do resumo
    # e algum trecho da transcrição para a frase contar como apoiada.
    grounding_threshold: float = 0.80
