"""Application Configuration."""


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    # "production" no docker-compose; "development" libera o transcritor de
    # mentira, usado só sem os modelos instalados.
    app_env: str = "development"
    LIGHTWEIGHT_BOOTSTRAP: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./app.db"

    # Origens aceitas pelo CORS, separadas por vírgula (CORS_ORIGINS). Em
    # produção o frontend chega pelo proxy do Nginx, na mesma origem.
    cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Ollama (LLM local): endereço do servidor e modelos padrão
    ollama_host: str = "http://localhost:11434"
    llm_model: str = "qwen3.5:9b"
    llm_fallback_model: str = "gemma4:e4b"
    # 16k tokens: cabe nos prompts do pipeline (síntese em blocos) sem que o
    # cache de contexto do Ollama ocupe GBs a mais da GPU de 12 GB.
    llm_context_tokens: int = 16384
    llm_timeout_seconds: int = 900
    # Tempo máximo de uma análise no worker. Fica abaixo do prazo em que a
    # mídia "em análise" é dada como falha (MEDIA_ANALYSIS_GIVE_UP_MINUTES,
    # 180), para que a falha venha da própria análise, com o motivo.
    analysis_time_limit_minutes: float = 150
    # Fatores opcionais da análise, separados por vírgula: sentiment, topics
    # (temas e seus títulos), grounding (verificação de fidelidade), chapters
    # (capítulos com horário) e questions (perguntas de revisão).
    analysis_factors: str = "sentiment,topics,grounding,chapters,questions"
    # Trechos da análise (em caracteres): a base dos vetores, dos temas e da
    # busca. Trocar o tamanho vale para as próximas análises.
    analysis_chunk_size: int = 512
    analysis_chunk_overlap: int = 64
    # Transcrições até este tamanho (~20 min de fala) vão inteiras à síntese e
    # às perguntas; acima, a síntese resume blocos de
    # ANALYSIS_SYNTHESIS_BLOCK_CHARS e une os resumos parciais, e as perguntas
    # partem do resumo. Com 36 mil, uma aula de 30 min ia numa chamada só e o
    # resumo pulava partes.
    analysis_full_transcript_chars: int = 18000
    analysis_synthesis_block_chars: int = 18000
    # Tamanho do resumo: SUMMARY_PERCENT % das palavras da transcrição, com no
    # mínimo SUMMARY_MIN_WORDS (sem máximo: uma aula de 2 h, com ~18 mil
    # palavras, pede ~2.200). Até SUMMARY_SHORT_WORDS, formato curto (sem
    # seções): um resumo com título, seções e pontos-chave ficava do tamanho
    # de uma fala curta.
    summary_percent: float = 12
    summary_min_words: int = 120
    summary_short_words: int = 200
    # Similaridade mínima (cosseno, multilingual-e5) entre uma frase do resumo
    # e algum trecho da transcrição para a frase contar como apoiada.
    grounding_threshold: float = 0.80
    # Capítulos: gravações abaixo de CHAPTERS_MIN_RECORDING_MINUTES ficam sem
    # capítulos; um capítulo tem no mínimo CHAPTERS_MIN_MINUTES e há no máximo
    # CHAPTERS_MAX. Sem temas que dividam a gravação, um a cada
    # CHAPTERS_EVERY_MINUTES.
    chapters_min_recording_minutes: float = 4
    chapters_min_minutes: float = 2
    chapters_max: int = 10
    chapters_every_minutes: float = 5
    # Revisão espaçada: dias até a próxima revisão em cada caixa (a 1ª é a de
    # quem errou ou nunca respondeu; 0 = hoje) e a caixa a partir da qual a
    # pergunta conta como dominada. Com o padrão, três acertos seguidos.
    review_interval_days: str = "0,1,3,7,14"
    review_mastered_box: int = 4
    # Tentativas de uma tarefa do pipeline além da primeira, e a espera antes
    # da tentativa n: PIPELINE_RETRY_BASE_SECONDS * 2^(n-1), até
    # PIPELINE_RETRY_MAX_SECONDS. Cada tentativa pode ocupar a GPU por muito
    # tempo.
    pipeline_max_retries: int = 3
    pipeline_retry_base_seconds: int = 30
    pipeline_retry_max_seconds: int = 600
    # Máximo de mídias com falha que o administrador reprocessa de uma vez.
    admin_bulk_reprocess_max: int = 200
    # Descrição de quadros de vídeo: "ollama" (padrão; o mesmo Qwen3.5 do
    # resumo, que aceita imagens), "moondream" ou "none" (desligada).
    # Comparados nos mesmos quadros de uma aula: o Qwen3.5 descreve em
    # português e transcreve os textos da tela (nomes, títulos de livros), o
    # Moondream só dizia "um homem fala ao microfone"; e não carrega um
    # segundo modelo de ~4 GB na GPU. Custa ~4 s por quadro (Moondream, ~2 s).
    visual_provider: str = "ollama"
    visual_ollama_model: str = "qwen3.5:9b"

    # AI / Machine Learning Hardware
    # Options: "auto", "cuda", "cpu", "rocm"
    ai_device: str = "auto"
    # Options: "float16", "float32", "int8", "int8_float16"
    ai_compute_type: str = "default"
    # Modelo de transcrição (Faster-Whisper ou openai-whisper).
    whisper_model: str = "large-v3-turbo"
    # Termos do domínio (separados por vírgula) que orientam a transcrição.
    # O Whisper acerta a fala comum e erra justo o jargão: numa aula de
    # engenharia de software, "overengineering" saiu "o Wolverine de Neil" e
    # "KISS, DRY e YAGNI" saiu "Keys, Draw e Agni". Vazio: sem glossário.
    whisper_hotwords: str = ""
    # Reranqueador da busca semântica: reordena os 20 trechos mais parecidos
    # lendo pergunta e trecho juntos. Numa aula de 30 min, o trecho certo
    # ficou em 1º em 7 de 8 perguntas (4 de 8 só com os vetores). Roda na CPU
    # da API (~2 GB de memória). Vazio: só os vetores.
    search_reranker_model: str = "BAAI/bge-reranker-v2-m3"
    # Candidatos que a busca por vetores traz para o reranqueador ordenar.
    # Medido numa aula de 30 min (8 perguntas formuladas com outras palavras):
    # o trecho certo ficava em 1º em 4 de 8 só com os vetores e em 7 de 8
    # reordenando os 20 primeiros. Mais candidatos, busca mais lenta na CPU.
    search_rerank_candidates: int = 20

    @property
    def resolved_device(self) -> str:
        """Determines the actual device to use based on settings and hardware."""
        import torch
        if self.ai_device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            # ROCm typically maps to 'cuda' in torch if properly installed
            return "cpu"
        if self.ai_device in ("cuda", "rocm") and not torch.cuda.is_available():
            # GPU pedida num contêiner sem GPU (era o caso da API): na CPU os
            # modelos funcionam; com "cuda", não carregavam.
            return "cpu"
        return self.ai_device

    @property
    def sync_database_url(self) -> str:
        """URL com driver síncrono (psycopg2/sqlite), para scripts e migrações."""
        if "+asyncpg" in self.database_url:
            return self.database_url.replace("+asyncpg", "+psycopg2")
        if "+aiosqlite" in self.database_url:
            return self.database_url.replace("+aiosqlite", "")
        return self.database_url

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
