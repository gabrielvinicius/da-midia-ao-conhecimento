import { useTopicModeling } from "../hooks/useTopicModeling";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";

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
      return <p className="text-destructive text-center">Error loading topics.</p>;
    }

    if (!analysis || !analysis.result?.topics) {
      return <p className="text-muted-foreground text-center">Awaiting analysis...</p>;
    }

    const topics = analysis.result.topics as string[];

    return (
      <div className="flex flex-wrap gap-2">
        {topics.map((topic) => (
          <Badge key={topic} variant="secondary" className="text-sm">
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
      <CardContent>
        {renderContent()}
      </CardContent>
    </Card>
  );
};
