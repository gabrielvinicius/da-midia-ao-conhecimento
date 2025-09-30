import { useTranscription } from "../hooks/useTranscription";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/Card";
import { Skeleton } from "../../../components/ui/Skeleton";
import { Badge } from "../../../components/ui/Badge";
import { TranscriptionStatus } from "../../../types";

interface TranscriptionPanelProps {
  mediaId: string;
}

export const TranscriptionPanel = ({ mediaId }: TranscriptionPanelProps) => {
  const { data: transcription, isLoading, isError } = useTranscription(mediaId);

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
      return <p className="text-destructive">Error loading transcription.</p>;
    }

    if (!transcription) {
      return <p className="text-muted-foreground">Transcription has not started yet.</p>;
    }

    switch (transcription.status) {
      case TranscriptionStatus.PENDING:
      case TranscriptionStatus.PROCESSING:
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Skeleton className="h-4 w-4 rounded-full" />
            <span>Processing transcription... This may take a few minutes.</span>
          </div>
        );
      case TranscriptionStatus.COMPLETED:
        return <p className="whitespace-pre-wrap">{transcription.text}</p>;
      case TranscriptionStatus.FAILED:
        return (
          <p className="text-destructive">
            Transcription failed: {transcription.error_message || "Unknown error"}
          </p>
        );
      default:
        return <p className="text-muted-foreground">Unknown transcription status.</p>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>Transcription</span>
          {transcription && <Badge variant="secondary">{transcription.status}</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {renderContent()}
      </CardContent>
    </Card>
  );
};
