import { useMemo } from "react";
import { useSentimentAnalysis } from "../hooks/useSentimentAnalysis";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ThumbsUp, ThumbsDown, Meh, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";

interface SentimentResultPanelProps {
  mediaId: string;
}

const sentimentConfig: Record<string, { icon: React.ReactNode; accent: string; label: string }> = {
  POSITIVE: { icon: <ThumbsUp className="h-8 w-8" />, accent: "text-emerald-500", label: "Positivo" },
  NEGATIVE: { icon: <ThumbsDown className="h-8 w-8" />, accent: "text-red-500", label: "Negativo" },
  NEUTRAL: { icon: <Meh className="h-8 w-8" />, accent: "text-amber-500", label: "Neutro" },
  ERROR: { icon: <Meh className="h-8 w-8" />, accent: "text-slate-500", label: "Erro na Análise" },
};

export const SentimentResultPanel = ({ mediaId }: SentimentResultPanelProps) => {
  const { data: analysis, isLoading, isError } = useSentimentAnalysis(mediaId);

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
          Aguarde: liberamos a análise assim que a transcrição estiver concluída.
        </div>
      );
    }

    const config = sentimentConfig[analysis.label] || sentimentConfig.NEUTRAL;
    const emotions = analysis.full_result?.emotions || {};
    const topEmotions = Object.entries(emotions)
      .sort(([, a], [, b]) => Number(b) - Number(a))
      .slice(0, 4);
    const scorePercent = Math.round(((analysis.score ?? 0) + 1) * 50);
    const confidencePercent = Math.round((analysis.confidence ?? 0) * 100);

    return (
      <div className="space-y-5">
        <div className="rounded-2xl border border-[#f2eadf] bg-[#fdfbf6] p-4 text-center shadow-sm">
          <div className={cn("mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-white", config.accent)}>
            {config.icon}
          </div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">sentimento</p>
          <p className="text-2xl font-bold text-slate-900">{config.label}</p>
          <p className="text-sm text-muted-foreground">
            Intensidade {scorePercent}% · Confiança {confidencePercent}%
          </p>
        </div>

        {topEmotions.length > 0 && (
          <div className="space-y-3">
            <p className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-500">
              <Sparkles className="h-4 w-4" /> Emoções predominantes
            </p>
            {topEmotions.map(([emotion, value]) => {
              const percent = Math.round(Number(value) * 100);
              return (
                <div key={emotion} className="space-y-1">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span className="capitalize">{emotion}</span>
                    <span>{percent}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted">
                    <div className="h-2 rounded-full bg-gradient-to-r from-emerald-400 via-amber-300 to-pink-300" style={{ width: `${percent}%` }} />
                  </div>
                </div>
              );
            })}
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
            Provider {analysis.provider}
            {analysis.full_result?.processing_time && (
              <> · {analysis.full_result.processing_time?.toFixed?.(1) ?? analysis.full_result.processing_time}s</>
            )}
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
