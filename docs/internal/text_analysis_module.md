# Módulo Text Analysis - Documentação Técnica (v7.0)

Este documento descreve a arquitetura, o fluxo de dados e os componentes internos do módulo de Análise de Texto, responsável por transformar transcrições brutas e contexto visual em insights estruturados e artigos interpretativos.

## Visão Geral da Arquitetura

O módulo segue os princípios da **Clean Architecture** (Arquitetura Hexagonal) e utiliza o padrão **Pipeline** para orquestrar o processamento.

- **Domain:** Entidades (`Analysis`, `Topic`, `Document`) e Interfaces (`Ports`).
- **Application:** Serviços (`TextAnalysisService`) e Steps do Pipeline.
- **Infrastructure:** Adaptadores para bibliotecas externas (`BERTopic`, `Transformers`, `Ollama`).

### Fluxo do Pipeline (Otimizado Level 8.0)

O processamento ocorre de forma sequencial e resiliente através da classe `AnalysisPipeline`.

1.  **Chunking (`ChunkingStep`):**
    -   Divide a transcrição longa em segmentos menores (ex: 512 tokens) com sobreposição.
    -   Essencial para respeitar o limite de contexto dos modelos de Embedding e LLM.

2.  **Topic Modeling & Summarization (`TopicModelingStep`):**
    -   **Engine:** BERTopic.
    -   **Otimização:** Utiliza a feature `representation_model` do BERTopic integrada com o Llama 3 (via Transformers Pipeline).
    -   **Processo:** Clusteriza os chunks semanticamente e gera um resumo interpretativo para cada tópico *durante* a modelagem, economizando uma passada de inferência.
    -   **Saída:** Lista de objetos `Topic` com palavras-chave e resumo.

3.  **Knowledge Indexing (`KnowledgeIndexingStep`):**
    -   Persiste os chunks e seus embeddings vetoriais no banco de dados (tabela `knowledge_chunks` com pgvector).
    -   Habilita a busca semântica futura (RAG).

4.  **Visual Insight (`VisualInsightStep`):**
    -   **Engine:** Moondream (via `VisualAnalysisPort`).
    -   **Processo:** Baixa o vídeo original, extrai frames chave (ex: 10%, 50%, 90% do tempo) e gera descrições textuais do que está sendo mostrado.
    -   **Objetivo:** Enriquecer o resumo final com contexto visual (ex: "O vídeo mostra um diagrama de classes...").

5.  **Synthesis (`SynthesisStep` - The "Journalist"):**
    -   **Engine:** Llama 3.1 8B Instruct.
    -   **Processo:** Recebe os resumos dos tópicos (passo 2) e o contexto visual (passo 4).
    -   **Prompt:** Utiliza prompts avançados ("Chain of Thought") dinâmicos baseados no idioma (PT/EN/ES) para escrever um artigo completo.
    -   **Saída:** Um texto fluido, coeso e formatado em Markdown, que serve como o "Resumo Final" para o usuário.

---

## Detalhes de Implementação

### Adaptadores Principais

*   **`BERTopicAdapter`:**
    *   Configura o BERTopic com `SentenceTransformer` (embeddings) e `KeyBERTInspired` (palavras-chave); os títulos dos temas vêm do LLM principal no `TopicTitleStep`.
    *   Possui fallback automático para TF-IDF/Keywords se o modelo neural falhar ou não encontrar tópicos.

*   **`OllamaTextGenerationAdapter`:**
    *   Única via de geração de texto (resumo e títulos), com modelo de reserva quando o principal falha.

### Resiliência e Otimização

*   **Async/Sync:** O pipeline roda em um Worker Celery dedicado (`worker-heavy`) para não bloquear a API. Operações pesadas de CPU/GPU são isoladas.
*   **Fallback:** Se a Síntese falhar, o sistema concatena os resumos dos tópicos como fallback.
*   **Hardware Agnostic:** O código verifica `settings.resolved_device` para decidir entre carregar modelos na GPU ou CPU.

## Manutenção

Para adicionar novos idiomas ao `SynthesisStep`:
1.  Edite `src/text_analysis/application/pipeline/steps.py`.
2.  Adicione a chave do idioma (ex: `"fr"`) no método `_get_prompt_template`.

Para alterar o modelo de LLM:
1.  Edite `src/text_analysis/application/config.py` e ajuste `transformer_representation_model`.
