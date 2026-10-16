# Modelos e etapas da análise

Todos os modelos rodam na própria máquina, e trocá-los é mudar configuração,
sem tocar no código: cada modelo fica atrás de uma porta, e o adaptador lê o
nome do `.env`. Este guia mostra as trocas mais comuns. Os tempos e a memória
de cada modelo estão na [referência dos modelos](../referencia/modelos.md).

Depois de mudar o `.env`, aplique com:

```powershell
docker compose up -d
```

O Compose recria só os serviços cuja configuração mudou. Os workers leem os
modelos ao iniciar, então uma troca não vale para uma análise já em andamento.

## Trocar o modelo de linguagem

O resumo, os títulos dos temas e dos capítulos, as perguntas e o gênero do
conteúdo saem do modelo de linguagem, servido pelo Ollama.

```env
LLM_MODEL=qwen3.5:9b          # principal
LLM_FALLBACK_MODEL=gemma4:e4b # reserva, se o principal falhar
LLM_CONTEXT_TOKENS=16384
```

- Use qualquer nome da [biblioteca do Ollama](https://ollama.com/library). O
  serviço `ollama-models` baixa o principal e o reserva ao subir; para baixar
  sem reiniciar: `docker compose exec ollama ollama pull <modelo>`.
- O modelo precisa caber na GPU junto com o contexto. Na placa de 12 GB, o
  Qwen3.5-9B quantizado com 16 k de contexto ocupa cerca de 7 GB.
- Um contexto maior aceita textos mais longos sem dividir a síntese em
  blocos, mas o cache do Ollama ocupa mais memória da GPU.

## Trocar o modelo de transcrição

```env
WHISPER_MODEL=large-v3-turbo
WHISPER_HOTWORDS=overengineering,KISS,DRY,YAGNI
```

- Modelos menores (`medium`, `small`) são mais rápidos e erram mais.
- `WHISPER_HOTWORDS` é um glossário: termos do domínio, separados por
  vírgula, que orientam a grafia. O Whisper acerta a fala comum e erra justo
  o jargão; o glossário corrige boa parte disso.

## Descrição dos quadros do vídeo

```env
VISUAL_PROVIDER=ollama           # ollama (padrão), moondream ou none
VISUAL_OLLAMA_MODEL=qwen3.5:9b
```

- `ollama` usa o mesmo modelo do resumo, que aceita imagens: descreve em
  português e transcreve os textos da tela, sem carregar um segundo modelo.
- `moondream` usa o Moondream 2 (cerca de 4 GB a mais na GPU).
- `none` desliga a etapa: nenhum modelo de visão é carregado.

## Ligar e desligar etapas da análise

Cinco etapas são opcionais. Liste as que devem rodar:

```env
ANALYSIS_FACTORS=sentiment,topics,grounding,chapters,questions
```

| Fator | Etapa |
|---|---|
| `sentiment` | Tom ao longo da gravação |
| `topics` | Temas e seus títulos |
| `grounding` | Verificação de fidelidade do resumo |
| `chapters` | Capítulos com horário (dependem dos temas) |
| `questions` | Perguntas de revisão |

Uma etapa desligada sai do pipeline e o modelo dela nem é carregado; as
seguintes funcionam sem ela. A divisão em trechos, os vetores, a indexação, o
gênero e o resumo sempre rodam.

## Reordenação da busca

```env
SEARCH_RERANKER_MODEL=BAAI/bge-reranker-v2-m3
```

O reranqueador lê a pergunta e cada um dos 20 trechos mais parecidos e os
reordena, na CPU da API. Vazio, a busca usa só a proximidade dos vetores: mais
rápida e menos precisa.

## Máquinas sem GPU NVIDIA

| Máquina | Como subir |
|---|---|
| GPU NVIDIA (referência) | `docker compose up -d --build` |
| Sem GPU | `docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build` |
| GPU AMD (ROCm) | `docker compose -f docker-compose.yml -f docker-compose.rocm.yml up -d --build` |

- **Sem GPU**: tudo funciona, mas a transcrição e o resumo ficam muitas
  vezes mais lentos.
- **GPU AMD**: o PyTorch usa o ROCm 7.2, e a transcrição (CTranslate2) passa
  sozinha para a CPU. Essa variante não foi testada numa placa AMD.

## Veja também

- [Pipeline de processamento](../explicacao/pipeline.md): onde cada modelo
  entra.
- ADR-011 (quadros pelo mesmo modelo do resumo), ADR-012 (reranqueador na CPU)
  e ADR-014 (PyTorch e CUDA), em [decisões](../adr/decisions.md).
