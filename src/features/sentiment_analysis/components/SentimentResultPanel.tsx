import type { ReactNode } from "react";
import { useTextAnalysisByMediaIdQuery } from "@/hooks/useQueries";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ThumbsUp, ThumbsDown, Meh, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { MediaStatus } from "@/types";

interface SentimentResultPanelProps {
  mediaId: string;
  mediaStatus?: MediaStatus;
}

const sentimentConfig: Record<string, { icon: ReactNode; accent: string; label: string }> = {
  POSITIVE: { icon: <ThumbsUp className="h-8 w-8" />, accent: "text-emerald-500", label: "Positivo" },
  NEGATIVE: { icon: <ThumbsDown className="h-8 w-8" />, accent: "text-red-500", label: "Negativo" },
  NEUTRAL: { icon: <Meh className="h-8 w-8" />, accent: "text-amber-500", label: "Neutro" },
  ERROR: { icon: <Meh className="h-8 w-8" />, accent: "text-slate-500", label: "Erro na Análise" },
};

export const SentimentResultPanel = ({ mediaId, mediaStatus }: SentimentResultPanelProps) => {
  const { data: analysis, isLoading, isError } = useTextAnalysisByMediaIdQuery(mediaId);

  const renderContent = () => {
    if (isLoading && !analysis) {
      return (
        <div className="space-y-2 flex flex-col items-center">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-16" />
        </div>
      );
    }

    if (isError) {
      return <p className="text-destructive text-center text-xs">Erro ao carregar análise.</p>;
    }

    if (!analysis) {
      return (
        <div className="rounded-2xl border border-[#f2eadf] bg-[#fdfbf6] p-4 text-center text-xs text-muted-foreground">
          {mediaStatus === MediaStatus.FAILED
            ? "Falha no processamento. Corrija o erro e tente reprocessar."
            : "Aguarde: liberamos a análise assim que a transcrição/extração estiver concluída."}
        </div>
      );
    }

    const label = String(analysis.overall_sentiment || "NEUTRAL").toUpperCase();
    const config = sentimentConfig[label] || sentimentConfig.NEUTRAL;
    const chunks = analysis.sentiment_items?.length ?? 0;

    return (
      <div className="space-y-5">
        <div className="rounded-2xl border border-[#f2eadf] bg-[#fdfbf6] p-4 text-center shadow-sm">
          <div className={cn("mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-white", config.accent)}>
            {config.icon}
          </div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">sentimento</p>
          <p className="text-2xl font-bold text-slate-900">{config.label}</p>
          <p className="text-sm text-muted-foreground">Baseado em {chunks} blocos de texto</p>
        </div>

        {(analysis.sentiment_items || []).slice(0, 4).length > 0 && (
          <div className="space-y-3">
            <p className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-500">
              <Sparkles className="h-4 w-4" /> Amostra de blocos
            </p>
            {(analysis.sentiment_items || []).slice(0, 4).map((item) => (
              <div key={item.chunk_id} className="rounded-xl border border-[#f2eadf] bg-[#fdfbf6] p-3 text-xs">
                <p className="font-semibold text-slate-900">{String(item.label).toUpperCase()}</p>
                <p className="mt-1 text-muted-foreground line-clamp-3">{item.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <Card className="border border-[#ede4d5] bg-gradient-to-br from-purple-900/10 text-slate-900">
      <CardHeader className="text-center space-y-1">
        <p className="text-xs uppercase tracking-[0.4em] text-muted-foreground">Tempo real</p>
        <CardTitle className="text-2xl">Análise de Sentimento</CardTitle>
        {analysis && (
          <CardDescription className="text-xs text-muted-foreground">
            {analysis.provider ? `Provider ${analysis.provider}` : "Provider automático"}
          </CardDescription>
        )}
        {!analysis && (
          <Badge variant="secondary" className="mx-auto w-fit rounded-full border border-[#f2eadf] bg-[#fdfbf6] text-slate-800">
            Em preparação
          </Badge>
        )}
      </CardHeader>
      <CardContent className="pt-4">
        {renderContent()}
      </CardContent>
    </Card>
  );
};
