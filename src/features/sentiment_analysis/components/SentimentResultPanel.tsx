import { useSentimentAnalysis } from "../hooks/useSentimentAnalysis";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ThumbsUp, ThumbsDown, Meh } from "lucide-react";
import * as React from "react";

interface SentimentResultPanelProps {
  mediaId: string;
}

const sentimentConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  POSITIVE: { icon: <ThumbsUp className="h-8 w-8" />, color: "text-green-500", label: "Positive" },
  NEGATIVE: { icon: <ThumbsDown className="h-8 w-8" />, color: "text-red-500", label: "Negative" },
  NEUTRAL: { icon: <Meh className="h-8 w-8" />, color: "text-yellow-500", label: "Neutral" },
  ERROR: { icon: <Meh className="h-8 w-8" />, color: "text-gray-500", label: "Analysis Error" },
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
      return <p className="text-destructive text-center text-xs">Error loading analysis.</p>;
    }

    if (!analysis) {
      return <p className="text-muted-foreground text-center text-xs">Awaiting text content to start analysis...</p>;
    }

    // Correctly access the flat structure of the response
    const config = sentimentConfig[analysis.label] || sentimentConfig.NEUTRAL;

    return (
      <div className={`flex flex-col items-center justify-center space-y-2 ${config.color}`}>
        {config.icon}
        <span className="text-xl font-bold">{config.label}</span>
        <span className="text-sm text-muted-foreground">Score: {analysis.score.toFixed(2)}</span>
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center">Sentiment Analysis</CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        {renderContent()}
      </CardContent>
    </Card>
  );
};
