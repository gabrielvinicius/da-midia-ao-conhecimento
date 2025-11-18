import { useTopicModeling } from "../hooks/useTopicModeling";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { TopicModelingStatus } from "@/types";
import { formatDistanceToNow } from "date-fns";

interface TopicModelingResultPanelProps {
  mediaId: string;
}

export const TopicModelingResultPanel = ({ mediaId }: TopicModelingResultPanelProps) => {
  const { data: analysis, isLoading, isError } = useTopicModeling(mediaId);

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
      return <p className="text-destructive text-center text-xs">Error loading topics.</p>;
    }

    if (!analysis) {
      return <p className="text-muted-foreground text-center text-xs">Awaiting topic modeling...</p>;
    }

    const rawTopics = analysis.raw_topics;
    if ((!rawTopics || rawTopics.length === 0) && (!analysis.topics || analysis.topics.length === 0)) {
      return (
        <p className="text-muted-foreground text-center text-xs">
          {analysis.status === TopicModelingStatus.PROCESSING
            ? "Topic modeling is processing..."
            : "Topics will appear after the transcription is completed."}
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
            const label = topic.name || topic.label || `Topic ${index + 1}`;
            const sentence = keywords.length
              ? `${label} destaca ${keywords.slice(0, -1).join(", ")} e ${keywords[keywords.length - 1]}.`
              : `${label} possui pouca informação disponível.`;
            return (
              <div key={topic.id ?? index} className="rounded-md border border-border/60 p-3 bg-muted/40">
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
    <Card>
      <CardHeader>
        <CardTitle className="text-center">Key Topics</CardTitle>
        {analysis && (
          <CardDescription className="text-xs text-center">
            Provider {analysis.provider ?? "sklearn_lda"}
            {analysis.processed_at && (
              <>
                {' '}- updated {formatDistanceToNow(new Date(analysis.processed_at), { addSuffix: true })}
              </>
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
