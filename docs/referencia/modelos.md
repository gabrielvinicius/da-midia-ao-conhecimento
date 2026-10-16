# Modelos de IA do pipeline

Todos rodam localmente; nenhum conteúdo é enviado a serviços externos. Os
tempos e a memória abaixo foram medidos numa RTX 3060 12 GB (i5-12400F, 32 GB),
com uma aula em vídeo de 30 min.

## Etapas, na ordem

| Etapa | Modelo | Configuração | Medido (30 min de vídeo) |
|---|---|---|---|
| Transcrição | Faster-Whisper `large-v3-turbo` (CTranslate2, float16) | `WHISPER_MODEL`, glossário em `WHISPER_HOTWORDS` | 62–84 s |
| Descrição dos quadros | Qwen3.5-9B via Ollama (padrão) ou Moondream 2 | `VISUAL_PROVIDER` (`ollama`, `moondream`, `none`), `VISUAL_OLLAMA_MODEL` | 33 s (8 quadros) |
| Divisão em trechos | segmentos agrupados até `chunk_size`, com início e fim | `AnalysisConfig.chunk_size` | < 1 s |
| Vetores dos trechos | `intfloat/multilingual-e5-small` (384 dim., prefixos `passage:`/`query:`) | `AnalysisConfig.embedding_model` (a dimensão precisa bater com `knowledge_chunks.embedding`) | < 1 s |
| Sentimento (fator `sentiment`) | `cardiffnlp/twitter-xlm-roberta-base-sentiment` | `AnalysisConfig.sentiment_model` | ~4 s |
| Temas (fator `topics`) | BERTopic sobre os mesmos vetores | `AnalysisConfig.topic_model` (`tfidf` para modo leve) | ~19 s |
| Indexação | pgvector | — | < 1 s |
| Títulos dos temas | LLM (Ollama) | `LLM_MODEL`, `LLM_FALLBACK_MODEL` | ~10 s |
| Gênero do conteúdo | LLM: aula, palestra, opinião, reunião, entrevista, tutorial, documento | sempre roda | ~1 s |
| Resumo | LLM; acima de ~20 min de fala, em blocos | `LLM_CONTEXT_TOKENS` | 60–90 s |
| Capítulos (fator `chapters`) | cortes pelos temas; títulos pelo LLM | — | ~3 s |
| Perguntas de revisão (fator `questions`) | LLM; cada resposta aponta o capítulo | — | ~7 s |
| Verificação de fidelidade (fator `grounding`) | mesmos vetores do e5 | `AnalysisConfig.grounding_threshold` | < 1 s |

Na busca (API, CPU): vetor da pergunta pelo e5-small e reordenação dos 20
trechos mais parecidos por `BAAI/bge-reranker-v2-m3` (`SEARCH_RERANKER_MODEL`;
vazio desliga), ~2,5 s por busca depois de carregado.

Os fatores opcionais ficam em `ANALYSIS_FACTORS`; desligado, o fator sai do
pipeline e o modelo dele nem é carregado.

## LLM via Ollama

O serviço `ollama` serve o modelo de linguagem; o serviço `ollama-models` baixa
o principal e o reserva na primeira inicialização. Variáveis (`.env.example`):

```env
LLM_MODEL=qwen3.5:9b
LLM_FALLBACK_MODEL=gemma4:e4b
LLM_CONTEXT_TOKENS=16384
```

- O modo de raciocínio (`think`) é desligado: só aumentaria o tempo de resposta.
- Se o modelo principal falhar, o adaptador tenta o reserva; se os dois
  falharem, a etapa recebe o erro e o resumo vira o simplificado (temas e
  palavras-chave), marcado como `simplified`.
- Se a resposta bater no teto de tokens, o adaptador pede a continuação (até
  duas vezes); se ainda faltar texto, o resumo termina na última frase
  completa e a análise marca `summary_truncated`.
- O Qwen3.5-9B aceita imagens: com `VISUAL_PROVIDER=ollama`, descreve os
  quadros em português e transcreve os textos da tela, sem carregar outro
  modelo na GPU.

## Memória da GPU (12 GB)

Pico medido de cada modelo, carregados um de cada vez pelo worker pesado:

| Componente | Pico |
|---|---|
| Faster-Whisper large-v3-turbo | ~1,5–2 GB |
| multilingual-e5-small | 0,5 GB |
| XLM-RoBERTa (sentimento) | 1,1 GB |
| BERTopic (com os vetores) | 2,2 GB |
| Moondream 2 (só com `VISUAL_PROVIDER=moondream`) | 4,1 GB |
| Qwen3.5-9B no Ollama, com contexto de 16 k | ~6,5–7 GB |

O Ollama descarrega o modelo após 5 min ocioso (`OLLAMA_KEEP_ALIVE`), e o
worker devolve a memória do PyTorch antes das etapas do Ollama.

## Diagnóstico de uma análise

Cada análise grava em `diagnostics`:

- `steps` e `step_seconds`: resultado (`ok` ou `failed: motivo`) e duração de
  cada etapa; o resultado parcial é salvo ao fim de cada etapa.
- `summary_source`: `llm`, `reserve` ou `simplified`; `summary_truncated`.
- `synthesis_input`: `full_transcript` ou `sections` (com `synthesis_sections`).
- `genre`, `chapters`, `review_questions`, `visual_context`.
- `grounding`: frases verificadas e apoiadas, janelas da gravação sem nenhuma
  frase do resumo (`gaps`) e números ausentes do trecho do assunto
  (`number_issues`).
- `indexed_chunks`, `sentiment_distribution`, `topic_titles_source`.
