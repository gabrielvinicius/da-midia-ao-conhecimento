import { useParams } from "react-router-dom";
import { useMediaDetail, useReprocessMedia } from "../features/media/hooks/useMedia";
import { InteractiveTranscriptionPanel } from "../features/transcription/components/InteractiveTranscriptionPanel";
import { SummaryPanel } from "../features/summarization/components/SummaryPanel";
import { SentimentResultPanel } from "@/features/sentiment_analysis/components/SentimentResultPanel";
import { TopicModelingResultPanel } from "@/features/topic_modeling/components/TopicModelingResultPanel"; // Re-enable v2 Feature
import { Skeleton } from "../components/ui/Skeleton";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useAuth } from "../contexts/AuthContext";
import { format } from "date-fns";
import { MediaType, MediaStatus } from "@/types";

const MediaDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  if (!id) {
    return <p>No media ID provided.</p>;
  }

  const { data: media, isLoading, isError } = useMediaDetail(id);
  const reprocessMutation = useReprocessMedia();

  const handleReprocess = () => {
    if (media) {
      reprocessMutation.mutate(media.id);
    }
  };

  if (isLoading) {
    // ... (Skeleton loading state remains the same)
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="mt-6 grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-8">
            <Skeleton className="h-96 w-full" />
          </div>
          <div className="lg:col-span-1 space-y-8">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !media) {
    return <p className="text-destructive">Error loading media details.</p>;
  }

  const isPlayable = media.media_type === MediaType.AUDIO || media.media_type === MediaType.VIDEO;

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold tracking-tight truncate">{media.original_file_path}</h1>
            <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
              <span>Uploaded on {format(new Date(media.created_at), "PPP")}</span>
              <Badge variant="outline">{media.media_type}</Badge>
              <Badge variant={media.status === MediaStatus.FAILED ? "destructive" : "secondary"}>{media.status}</Badge>
            </div>
          </div>
          {user?.role === 'admin' && media.status === MediaStatus.FAILED && (
            <Button 
              onClick={handleReprocess} 
              disabled={reprocessMutation.isPending}
              variant="outline"
            >
              {reprocessMutation.isPending ? "Reprocessing..." : "Reprocess"}
            </Button>
          )}
        </div>
        {media.status === MediaStatus.FAILED && media.error_message && (
          <div className="mt-4 p-4 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-sm font-semibold text-destructive">Processing Failed</p>
            <p className="text-xs text-destructive/80 mt-1">{media.error_message}</p>
          </div>
        )}
      </div>

      {/* Main Content Layout */}
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          {isPlayable ? (
            <InteractiveTranscriptionPanel mediaId={id} />
          ) : (
            <p className="text-center text-muted-foreground py-16">Interactive transcription is only available for audio and video files.</p>
          )}
        </div>
        <div className="lg:col-span-1 space-y-8">
          <SentimentResultPanel mediaId={id} />
          <TopicModelingResultPanel mediaId={id} />
          <SummaryPanel mediaId={id} />
        </div>
      </div>
    </div>
  );
};

export default MediaDetailPage;
