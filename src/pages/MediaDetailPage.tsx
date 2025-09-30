import { useParams } from "react-router-dom";
import { useMediaDetail } from "../features/media/hooks/useMedia";
import { InteractiveTranscriptionPanel } from "../features/transcription/components/InteractiveTranscriptionPanel";
import { SummaryPanel } from "../features/summarization/components/SummaryPanel";
// import { SentimentResultPanel } from "@/features/sentiment_analysis/components/SentimentResultPanel"; // v2 Feature
// import { TopicModelingResultPanel } from "@/features/sentiment_analysis/components/TopicModelingResultPanel"; // v2 Feature
import { Skeleton } from "../components/ui/Skeleton";
import { Badge } from "../components/ui/Badge";
import { format } from "date-fns";
import { MediaType } from "@/types";

const MediaDetailPage = () => {
  const { id } = useParams<{ id: string }>();

  if (!id) {
    return <p>No media ID provided.</p>;
  }

  const { data: media, isLoading, isError } = useMediaDetail(id);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="mt-6 grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-8">
            <Skeleton className="h-96 w-full" />
          </div>
          <div className="lg:col-span-1 space-y-8">
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
        <h1 className="text-3xl font-bold tracking-tight truncate">{media.original_file_path}</h1>
        <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
          <span>Uploaded on {format(new Date(media.created_at), "PPP")}</span>
          <Badge variant="outline">{media.media_type}</Badge>
          <Badge variant="secondary">{media.status}</Badge>
        </div>
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
          {/* v2 Features - Commented out for v1 stability */}
          {/* <SentimentResultPanel mediaId={id} /> */}
          {/* <TopicModelingResultPanel mediaId={id} /> */}
          <SummaryPanel mediaId={id} />
        </div>
      </div>
    </div>
  );
};

export default MediaDetailPage;
