import { useTopicModeling } from "../hooks/useTopicModeling";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { TopicModelingStatus } from "@/types";
import { formatDistanceToNow } from "date-fns";
import { Brain, Clock3, Loader2, Sparkles } from "lucide-react";

interface TopicModelingResultPanelProps {
  mediaId: string;
}

const statusMap: Record<string, { label: string; variant: "default" | "secondary" | "destructive" }> = {
  [TopicModelingStatus.COMPLETED]: { label: "Concluído", variant: "default" },
  [TopicModelingStatus.PROCESSING]: { label: "Processando", variant: "secondary" },
  [TopicModelingStatus.FAILED]: { label: "Falhou", variant: "destructive" },
};

export const TopicModelingResultPanel = ({ mediaId }: TopicModelingResultPanelProps) => {
  const { data: analysis, isLoading, isError } = useTopicModeling(mediaId);

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
        <CardDescription className="flex flex-wrap items-center gap-2 text-xs">
          <Badge variant="outline" className="gap-1">
            <Sparkles className="h-3 w-3 text-amber-500" />
            {analysis?.provider ?? "sklearn_lda"}
          </Badge>
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
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4 relative">
        {renderContent()}
      </CardContent>
    </Card>
  );
};
