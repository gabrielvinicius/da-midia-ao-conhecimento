import { useTopicModeling } from "../hooks/useTopicModeling";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { TopicModelingStatus, TopicSummaryDetail } from "@/types";
import { formatDistanceToNow } from "date-fns";
import { Brain, Clock3, Loader2, Sparkles, Languages, ListOrdered } from "lucide-react";

interface TopicModelingResultPanelProps {
  mediaId: string;
}

const providerMeta: Record<string, { label: string; description: string }> = {
  sklearn_lda: {
    label: "Scikit-Learn LDA",
    description: "Modelo probabilístico equilibrado, ótimo para a maioria dos conteúdos.",
  },
  sklearn_lsa: {
    label: "SVD (LSA)",
    description: "Foca em componentes semânticos globais.",
  },
  sklearn_nmf: {
    label: "NMF Localizado",
    description: "Realça termos específicos por tópico.",
  },
  keyword_frequency: {
    label: "Frequência de Palavras",
    description: "Fallback leve para ambientes sem dependências extras.",
  },
  btm_simple: {
    label: "BTM Simplificado",
    description: "Ideal para conversas curtas e snippets.",
  },
  anchor_topics: {
    label: "Tópicos por Âncoras",
    description: "Categorias guiadas por palavras-chave definidas.",
  },
  semantic_clusters: {
    label: "Clusters Semânticos",
    description: "Agrupa blocos semelhantes via TF-IDF + KMeans.",
  },
  embedding_clusters: {
    label: "Clusters com Embeddings",
    description: "Requer sentence-transformers para detecção mais rica.",
  },
  bertopic: {
    label: "BERTopic",
    description: "Modelo avançado baseado em embeddings e UMAP/HDBSCAN.",
  },
};

const statusMap: Record<string, { label: string; variant: "default" | "secondary" | "destructive" }> = {
  [TopicModelingStatus.COMPLETED]: { label: "Concluído", variant: "default" },
  [TopicModelingStatus.PROCESSING]: { label: "Processando", variant: "secondary" },
  [TopicModelingStatus.FAILED]: { label: "Falhou", variant: "destructive" },
};

export const TopicModelingResultPanel = ({ mediaId }: TopicModelingResultPanelProps) => {
  const { data: analysis, isLoading, isError } = useTopicModeling(mediaId);
  const providerInfo = analysis?.provider ? providerMeta[analysis.provider] : undefined;

  const renderStatusBadge = () => {
    const status = analysis?.status ?? TopicModelingStatus.PROCESSING;
    const config = statusMap[status] ?? statusMap[TopicModelingStatus.PROCESSING];
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const renderContent = () => {
    if (isLoading && !analysis) {
      return (
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-20 rounded-full" />
          ))}
        </div>
      );
    }

    if (isError) {
      return <p className="text-destructive text-center text-xs">Não foi possível carregar os tópicos.</p>;
    }

    if (!analysis) {
    return (
      <p className="text-muted-foreground text-center text-xs flex items-center justify-center gap-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Modelagem em andamento... aguarde alguns instantes.
      </p>
      );
    }

    const metaItems: React.ReactNode[] = [];
    if (analysis?.language) {
      metaItems.push(
        <span key="language" className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5">
          <Languages className="h-3 w-3" />
          Idioma: {analysis.language.toUpperCase()}
        </span>
      );
    }
    if (analysis?.num_topics) {
      metaItems.push(
        <span key="topics" className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5">
          <ListOrdered className="h-3 w-3" />
          {analysis.num_topics} tópicos
        </span>
      );
    }
    if (analysis?.model_name) {
      metaItems.push(
        <span key="model" className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5">
          Modelo: {analysis.model_name}
        </span>
      );
    }
    const metaBadges = metaItems.length > 0 ? (
      <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">{metaItems}</div>
    ) : null;

    const structuredTopics = analysis.topic_summaries;
    if (structuredTopics && structuredTopics.length > 0) {
      return (
        <div className="space-y-3 text-sm leading-relaxed">
          {metaBadges}
          {structuredTopics.map((topic: TopicSummaryDetail, index: number) => (
            <div
              key={topic.id ?? index}
              className="rounded-2xl border border-[#f2eadf] bg-[#fdfbf6] p-3 shadow-sm"
            >
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">{topic.label}</p>
              {topic.summary_sentence ? (
                <p className="mt-2 font-medium text-slate-900">{topic.summary_sentence}</p>
              ) : (
                <p className="mt-2 text-muted-foreground">
                  {topic.keywords.length
                    ? `Principais termos: ${topic.keywords.slice(0, 5).join(", ")}`
                    : "Em processamento..."}
                </p>
              )}
              {topic.keywords.length > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Palavras-chave: {topic.keywords.slice(0, 6).join(", ")}
                </p>
              )}
            </div>
          ))}
        </div>
      );
    }

    const rawTopics = analysis.raw_topics;
    if ((!rawTopics || rawTopics.length === 0) && (!analysis.topics || analysis.topics.length === 0)) {
      return (
        <p className="text-muted-foreground text-center text-xs">
          {analysis.status === TopicModelingStatus.PROCESSING
            ? "Estamos analisando o conteúdo para extrair os tópicos predominantes."
            : "Os tópicos serão exibidos assim que a transcrição e a sumarização forem concluídas."}
        </p>
      );
    }

    if (rawTopics && rawTopics.length > 0) {
      return (
        <div className="space-y-3 text-sm leading-relaxed">
          {metaBadges}
          {rawTopics.map((topic, index) => {
            const keywords = (topic.keywords || topic.terms || [])
              .map((keyword: any) =>
                typeof keyword === "string" ? keyword : keyword?.[0] || keyword?.term || keyword
              )
              .filter(Boolean)
              .slice(0, 6);
            const label = topic.name || topic.label || `Tópico ${index + 1}`;
            const sentence = keywords.length
              ? `${label} destaca ${keywords.slice(0, -1).join(", ")} e ${keywords[keywords.length - 1]}.`
              : `${label} ainda possui pouca informação disponível.`;
            return (
              <div
                key={topic.id ?? index}
                className="rounded-2xl border border-border/60 bg-gradient-to-r from-background via-background to-slate-900/5 p-3 shadow-sm"
              >
                <p>{sentence}</p>
              </div>
            );
          })}
        </div>
      );
    }

    return (
      <div className="space-y-2 text-sm">
        {(analysis.topics || []).map((topic, index) => (
          <p key={index}>{topic}</p>
        ))}
      </div>
    );
  };

  return (
    <Card className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-purple-500/10 via-transparent to-sky-500/10" />
      <CardHeader className="space-y-1 relative">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1 font-medium">
            <Brain className="h-3.5 w-3.5 text-purple-500" />
            Inteligência de tópicos
          </span>
          {analysis && renderStatusBadge()}
        </div>
        <CardTitle className="text-xl">Principais assuntos</CardTitle>
        <CardDescription className="flex flex-col gap-1 text-xs">
          <Badge variant="outline" className="gap-1">
            <Sparkles className="h-3 w-3 text-amber-500" />
            {providerInfo?.label ?? analysis?.provider ?? "sklearn_lda"}
          </Badge>
          {providerInfo?.description && (
            <span className="text-muted-foreground leading-relaxed">
              {providerInfo.description}
            </span>
          )}
          <div className="flex flex-wrap items-center gap-2">
            {analysis?.processed_at ? (
              <span className="inline-flex items-center gap-1">
                <Clock3 className="h-3.5 w-3.5" />
                Atualizado {formatDistanceToNow(new Date(analysis.processed_at), { addSuffix: true })}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-muted-foreground">
                <Clock3 className="h-3.5 w-3.5" />
                Aguardando processamento
              </span>
            )}
          </div>
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4 relative">
        {renderContent()}
      </CardContent>
    </Card>
  );
};
