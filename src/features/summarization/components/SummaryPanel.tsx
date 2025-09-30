import { useSummary } from "../hooks/useSummary";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/Card";
import { Skeleton } from "../../../components/ui/Skeleton";
import { Badge } from "../../../components/ui/Badge";
import { SummaryStatus } from "../../../types";

interface SummaryPanelProps {
  mediaId: string;
}

export const SummaryPanel = ({ mediaId }: SummaryPanelProps) => {
  const { data: summary, isLoading, isError } = useSummary(mediaId);

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="space-y-2">
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-20 w-full" />
        </div>
      );
    }

    if (isError) {
      return <p className="text-destructive">Error loading summary.</p>;
    }

    if (!summary) {
      return <p className="text-muted-foreground">Summary has not started yet.</p>;
    }

    switch (summary.status) {
      case SummaryStatus.PENDING:
      case SummaryStatus.PROCESSING:
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Skeleton className="h-4 w-4 rounded-full" />
            <span>Processing summary...</span>
          </div>
        );
      case SummaryStatus.COMPLETED:
        return <p className="whitespace-pre-wrap">{summary.text}</p>;
      case SummaryStatus.FAILED:
        return (
          <p className="text-destructive">
            Summary failed: {summary.error_message || "Unknown error"}
          </p>
        );
      default:
        return <p className="text-muted-foreground">Unknown summary status.</p>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>Summary</span>
          {summary && <Badge variant="secondary">{summary.status}</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {renderContent()}
      </CardContent>
    </Card>
  );
};
