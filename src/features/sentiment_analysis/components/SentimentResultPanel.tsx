import { useSentimentAnalysis } from "../hooks/useSentimentAnalysis";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ThumbsUp, ThumbsDown, Meh } from "lucide-react";
import * as React from "react";

interface SentimentResultPanelProps {
  mediaId: string;
}

const sentimentConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  POSITIVE: { icon: <ThumbsUp className="h-8 w-8" />, color: "text-green-500", label: "Positivo" },
  NEGATIVE: { icon: <ThumbsDown className="h-8 w-8" />, color: "text-red-500", label: "Negativo" },
  NEUTRAL: { icon: <Meh className="h-8 w-8" />, color: "text-yellow-500", label: "Neutro" },
  ERROR: { icon: <Meh className="h-8 w-8" />, color: "text-gray-500", label: "Erro na Análise" },
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
      return <p className="text-muted-foreground text-center text-xs">Aguardando conteúdo de texto para iniciar análise...</p>;
    }

    const config = sentimentConfig[analysis.label] || sentimentConfig.NEUTRAL;
    const emotions = analysis.full_result?.emotions || {};
    const topEmotions = Object.entries(emotions)
      .sort(([, a], [, b]) => Number(b) - Number(a))
      .slice(0, 4);
    const scorePercent = Math.round(((analysis.score ?? 0) + 1) * 50);
    const confidencePercent = Math.round((analysis.confidence ?? 0) * 100);

    return (
      <div className="space-y-4 w-full">
        <div className={`flex flex-col items-center justify-center space-y-2 ${config.color}`}>
          {config.icon}
          <span className="text-xl font-bold">{config.label}</span>
          <span className="text-sm text-muted-foreground">
            Pontuação: {scorePercent}% {analysis.score < 0 ? "negativo" : "positivo"}
          </span>
          {analysis.confidence !== undefined && (
            <span className="text-xs text-muted-foreground">
              Confiança {confidencePercent}%
            </span>
          )}
        </div>

        {topEmotions.length > 0 && (
          <div className="space-y-2">
            {topEmotions.map(([emotion, value]) => {
              const percent = Math.round(Number(value) * 100);
              return (
                <div key={emotion}>
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span className="capitalize">{emotion}</span>
                    <span>{percent}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted">
                    <div
                      className="h-2 rounded-full bg-primary"
                      style={{ width: `${percent}%` }}
                    />
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
    <Card>
      <CardHeader>
        <CardTitle className="text-center">Análise de Sentimento</CardTitle>
        {analysis && (
          <CardDescription className="text-center text-xs">
            Provider {analysis.provider}
            {analysis.full_result?.processing_time && (
              <> · {analysis.full_result.processing_time?.toFixed?.(1) ?? analysis.full_result.processing_time}s</>
            )}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="pt-4">
        {renderContent()}
      </CardContent>
    </Card>
  );
};
