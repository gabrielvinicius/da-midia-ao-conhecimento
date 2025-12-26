import { useTextAnalysisByMediaIdQuery } from "@/hooks/useQueries";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { MediaStatus, TextAnalysisTopic } from "@/types";
import { Brain, Clock3, Loader2, Sparkles, Languages, ListOrdered } from "lucide-react";

interface TopicModelingResultPanelProps {
  mediaId: string;
  mediaStatus?: MediaStatus;
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

export const TopicModelingResultPanel = ({ mediaId, mediaStatus }: TopicModelingResultPanelProps) => {
  const { data: analysis, isLoading, isError } = useTextAnalysisByMediaIdQuery(mediaId);
  const provider = analysis?.provider ?? undefined;
  const providerInfo = provider ? providerMeta[provider] : undefined;

  const renderStatusBadge = () => {
    if (mediaStatus === MediaStatus.FAILED) {
      return <Badge variant="destructive">Falhou</Badge>;
    }
    if (!analysis && mediaStatus === MediaStatus.PROCESSING) {
      return <Badge variant="secondary">Processando</Badge>;
    }
    if (analysis) {
      return <Badge variant="default">Concluído</Badge>;
    }
    return <Badge variant="secondary">Aguardando</Badge>;
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
          {mediaStatus === MediaStatus.PROCESSING
            ? "Modelagem em andamento... aguarde alguns instantes."
            : "Tópicos ainda não disponíveis."}
        </p>
      );
    }

    const metaItems: React.ReactNode[] = [];
    const language = analysis.diagnostics?.language || analysis.diagnostics?.lang || null;
    if (language) {
      metaItems.push(
        <span key="language" className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5">
          <Languages className="h-3 w-3" />
          Idioma: {String(language).toUpperCase()}
        </span>
      );
    }
    const numTopics = (analysis.topics || []).length;
    if (numTopics) {
      metaItems.push(
        <span key="topics" className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5">
          <ListOrdered className="h-3 w-3" />
          {numTopics} tópicos
        </span>
      );
    }
    const metaBadges = metaItems.length > 0 ? (
      <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">{metaItems}</div>
    ) : null;

    const topics = analysis.topics || [];
    if (topics.length > 0) {
      return (
        <div className="space-y-3 text-sm leading-relaxed">
          {metaBadges}
          {topics.map((topic: TextAnalysisTopic, index: number) => (
            <div
              key={topic.topic_id ?? index}
              className="rounded-2xl border border-[#f2eadf] bg-[#fdfbf6] p-3 shadow-sm"
            >
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">{topic.title || `Tópico ${index + 1}`}</p>
              {topic.summary_md ? (
                <p className="mt-2 font-medium text-slate-900 whitespace-pre-wrap">{topic.summary_md}</p>
              ) : (
                <p className="mt-2 text-muted-foreground">
                  {topic.keywords?.length
                    ? `Principais termos: ${topic.keywords.slice(0, 5).join(", ")}`
                    : "Sem resumo disponível."}
                </p>
              )}
              {topic.keywords?.length > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Palavras-chave: {topic.keywords.slice(0, 6).join(", ")}
                </p>
              )}
            </div>
          ))}
        </div>
      );
    }

    return <p className="text-muted-foreground text-center text-xs">Nenhum tópico detectado.</p>;
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
            {providerInfo?.label ?? provider ?? "automático"}
          </Badge>
          {providerInfo?.description && (
            <span className="text-muted-foreground leading-relaxed">
              {providerInfo.description}
            </span>
          )}
          <div className="flex flex-wrap items-center gap-2">
            {analysis ? null : (
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
