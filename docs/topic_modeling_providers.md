# Topic Modeling Providers

Esta nota resume os providers disponíveis após a última refatoração e como habilitá-los via variáveis de ambiente.

## Providers Disponíveis

| Provider             | Descrição                                                                 | Quando usar                                                                 | Habilitação |
|----------------------|----------------------------------------------------------------------------|------------------------------------------------------------------------------|-------------|
| `sklearn_lda`        | CountVectorizer + Latent Dirichlet Allocation.                             | Cenário padrão, equilíbrio entre performance e qualidade em textos médios.  | Já habilitado por default. |
| `sklearn_lsa`        | CountVectorizer + TruncatedSVD (LSA/LSI).                                  | Quando precisamos de tópicos mais globais/semânticos, menos sensíveis a ruído. | Incluir `sklearn_lsa` em `TOPIC_MODELING_ENABLED_PROVIDERS`.
| `sklearn_nmf`        | CountVectorizer + NMF.                                                     | Para tópicos mais localizados (palavras-chave bem concentradas).            | Incluir `sklearn_nmf` no ENV. |
| `keyword_frequency`  | Frequência de palavras (fallback).                                         | Ambientes sem scikit-learn ou tarefas rápidas sem dependências extras.      | Já habilitado, mas não default. |
| `btm_simple`         | Gibbs sampling simplificado estilo Biterm para textos curtos.              | Conversas curtas, resumos rápidos de segmentos curtos; requer ativação manual. | Adicionar `btm_simple` ao ENV. |
| `anchor_topics`      | Gera tópicos baseados em palavras âncora definidas em `options['anchors']`. | Quando precisamos de categorias predefinidas e interpretáveis.             | Adicionar `anchor_topics` e fornecer anchors no payload. |
| `semantic_clusters`  | TF-IDF + KMeans agrupando documentos por similaridade.                     | Quando queremos tópicos derivados de clusters semânticos (sem dependências extras). | Adicionar `semantic_clusters`. |
| `embedding_clusters` | SentenceTransformer + KMeans (requer `sentence-transformers`).              | Narrativas longas onde embeddings fornecem clusters mais ricos.                    | Instalar `sentence-transformers` e listar `embedding_clusters`. |
| `bertopic` (opcional)| Usa BERTopic (requer dependência externa).                                  | Somente se o pacote estiver instalado e embeddings forem necessários.       | Instalar dependência e habilitar no ENV. |

## Como habilitar/desabilitar

```bash
export TOPIC_MODELING_ENABLED_PROVIDERS="sklearn_lda,sklearn_lsa,sklearn_nmf,keyword_frequency,btm_simple,anchor_topics,semantic_clusters"
export TOPIC_MODELING_DEFAULT_PROVIDER="sklearn_lda"
```

Os providers adicionais só serão carregados se estiverem listados no ENV; nenhum deles substitui o default automaticamente.

## Avaliação de Qualidade (Plano)
1. **Dataset de teste**: usar transcrições reais com rótulos manuais (mínimo 5 mídias por idioma).
2. **Métricas**: medir coerência (UMASS/NP coherence), diversidade (tópicos distintos) e satisfação manual.
3. **Procedimento**:
   - Rodar cada provider com as mesmas opções (`num_topics`, `num_words`).
   - Registrar métricas no Prometheus (já temos hooks em `TopicModelingDomainService`).
   - Coletar feedback qualitativo via painel admin (campos "provider" já chegam no frontend).
4. **Critérios**:
   - Habilitar por default apenas providers com coerência > baseline e custo aceitável.
   - Manter `btm_simple`, `anchor_topics`, `semantic_clusters` como opcionais até passarem nesse checklist.

Documentar os resultados em `docs/internal/analysis/topic_modeling_eval.md` (a criar) quando o experimento rodar.
