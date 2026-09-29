# Providers de Sumarização

| Provider                 | Descrição                                                                 | Dependências                                   | Situação padrão |
|--------------------------|-----------------------------------------------------------------------------|------------------------------------------------|-----------------|
| `heuristic_interpretive` | Heurística com TextRank + narrativa interpretativa (timeline + quartis).  | Nenhuma                                        | ✅ habilitado   |
| `keyword_highlighter`    | Seleciona sentenças com maior densidade de palavras-chave.                 | Nenhuma                                        | ✅ habilitado   |
| `huggingface`            | Alias padrão (T5-base).                                                    | `transformers`, PyTorch                        | Opcional        |
| `huggingface_t5_base`    | T5-base focado em PT/EN curtos.                                            | `transformers`, PyTorch                        | Opcional        |
| `huggingface_bart_large` | BART-Large CNN (resumos longos em EN).                                     | `transformers`, PyTorch                        | Opcional        |
| `huggingface_pegasus`    | Pegasus Multi-News, bom para conteúdos extensos.                           | `transformers`, PyTorch                        | Opcional        |

## Como habilitar

Configurar via variáveis de ambiente:

```bash
export SUMMARIZATION_ENABLED_PROVIDERS="heuristic_interpretive,keyword_highlighter,huggingface"
export SUMMARIZATION_DEFAULT_PROVIDER="heuristic_interpretive"
export SUMMARIZATION_PROVIDER_OVERRIDES='{"huggingface": {"model_name": "google-t5/t5-large"}}'
```

* **HuggingFace**: aceitar `model_name`, `device` e limites de tokens.

## Registry Global
- O arquivo `providers.py` agora lista os providers acima em `/providers/summarization`.
- Workers Celery carregam apenas os providers presentes em `SUMMARIZATION_ENABLED_PROVIDERS`.

## Plano de Validação
1. Reprocessar um conjunto fixo de mídias (>=5 por idioma) com cada provider.
2. Gravar métricas de coerência/diversidade e tempo total.
3. Monitorar logs `summarization.domain.completed` com `provider`/`strategy` para telemetria.

## Provedores de Transcrição

O sistema suporta múltiplos provedores de transcrição via `TranscriptionService`.

### Opções Recomendadas
* **whisper-medium** (Default): Bom equilíbrio entre precisão e velocidade.
* **turbo** (`faster-whisper-large-v3-turbo`): **Recomendado para produção**. Qualidade de Large-v3 com velocidade de Medium.

### Configuração
Para alterar o modelo de transcrição, passe o parâmetro `transcription_provider` nas configurações ou requests.

Exemplo de override no `.env`:
```env
TRANSCRIPTION_DEFAULT_PROVIDER=turbo
```

