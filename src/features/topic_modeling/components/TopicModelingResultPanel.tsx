import { useTopicModeling } from "../hooks/useTopicModeling";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { TopicModelingStatus } from "@/types";

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

    if (!analysis || !analysis.topics || analysis.topics.length === 0) {
      return <p className="text-muted-foreground text-center text-xs">Awaiting text content to start analysis...</p>;
    }

    if (analysis.status !== TopicModelingStatus.COMPLETED) {
      return (
        <p className="text-muted-foreground text-center text-xs">
          {analysis.status === TopicModelingStatus.PROCESSING
            ? "Topic modeling is processing..."
            : "Topic modeling is not available yet."}
        </p>
      );
    }

    const topics = analysis.topics;

    return (
      <div className="flex flex-wrap gap-2 justify-center">
        {topics.map((topic, index) => (
          <Badge key={index} variant="secondary" className="text-sm">
            {topic}
          </Badge>
        ))}
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center">Key Topics</CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        {renderContent()}
      </CardContent>
    </Card>
  );
};
