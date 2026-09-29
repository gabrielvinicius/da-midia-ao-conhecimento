# Modelos de IA do pipeline

Visão geral dos modelos usados em cada etapa e de como trocá-los. Todos rodam
localmente; nenhum conteúdo é enviado a serviços externos.

| Etapa | Modelo padrão | Onde configurar |
|---|---|---|
| Transcrição | Faster-Whisper `large-v3-turbo` | `transcription_provider` no envio; sem provedor, usa o padrão real (`default`) |
| Divisão em trechos | Agrupa segmentos da transcrição até `chunk_size` caracteres, mantendo início e fim | `AnalysisConfig.chunk_size` |
| Sentimento | `cardiffnlp/twitter-xlm-roberta-base-sentiment` (positivo/neutro/negativo) | `AnalysisConfig.sentiment_model` |
| Embeddings (temas e busca) | `intfloat/multilingual-e5-small` (384 dimensões, com prefixos `passage:`/`query:`) | `AnalysisConfig.embedding_model` — a dimensão precisa bater com `knowledge_chunks.embedding` |
| Temas | BERTopic | `AnalysisConfig.topic_model` (`tfidf` para modo leve) |
| Títulos dos temas, resumo final | LLM via Ollama: `qwen3.5:9b`, reserva `gemma4:e4b` | `LLM_MODEL`, `LLM_FALLBACK_MODEL` |
| Descrição de quadros de vídeo | Moondream 2 | `VISUAL_PROVIDER=moondream` ou `ollama` (usa `VISUAL_OLLAMA_MODEL`) |

## LLM via Ollama

O serviço `ollama` do `docker-compose.yml` serve o modelo de linguagem. Na primeira
execução, baixe os modelos:

```bash
docker compose exec ollama ollama pull qwen3.5:9b
docker compose exec ollama ollama pull gemma4:e4b
```

Variáveis de ambiente (ver `.env.example`):

```env
OLLAMA_HOST=http://ollama:11434
LLM_MODEL=qwen3.5:9b
LLM_FALLBACK_MODEL=gemma4:e4b
LLM_CONTEXT_TOKENS=32768
```

- O modo de raciocínio (`think`) é desligado nas chamadas, pois só aumentaria o tempo de resposta.
- Se o modelo principal falhar, o adaptador tenta o reserva. Se ambos falharem, devolve um texto
  simples e o pipeline registra `diagnostics.summary_source = "fallback"`.
- Nomes com prefixo `hf:` (ex.: `hf:Qwen/Qwen2.5-7B-Instruct`) usam o adaptador Transformers
  em vez do Ollama; esse caminho exige `bitsandbytes` para modelos de 7B ou mais.

## Orçamento de memória (GPU de 12 GB)

Estimativas para uma RTX 3060 12 GB — confirme medindo no seu hardware:

| Componente | VRAM aproximada |
|---|---|
| Faster-Whisper large-v3-turbo | ~1,5–2 GB |
| multilingual-e5-small | ~0,5 GB |
| XLM-RoBERTa (sentimento) | ~1 GB |
| Moondream 2 (se `VISUAL_PROVIDER=moondream`) | ~4 GB |
| Qwen3.5-9B quantizado no Ollama, com contexto | ~6,5–7 GB |

O Ollama descarrega o modelo após 5 minutos ocioso (`OLLAMA_KEEP_ALIVE`). Com
`VISUAL_PROVIDER=ollama`, o Moondream deixa de ser carregado e a descrição dos quadros usa o
mesmo modelo do resumo.

## Diagnóstico de uma análise

Cada análise grava em `diagnostics`:

- `steps`: status de cada etapa (`ok` ou `failed: ...`); o resultado é salvo ao fim de cada etapa.
- `summary_source`: `llm`, `fallback` ou `error`.
- `synthesis_input`: `full_transcript` (transcrição inteira) ou `topics` (material por tema).
- `indexed_chunks`, `visual_frames`, `sentiment_distribution`, `topic_titles_source`.
