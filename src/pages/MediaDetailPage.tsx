import { useParams } from "react-router-dom";
import { useMediaDetail } from "../features/media/hooks/useMedia";
import { TranscriptionPanel } from "../features/transcription/components/TranscriptionPanel";
import { SummaryPanel } from "../features/summarization/components/SummaryPanel";
import { Skeleton } from "../components/ui/Skeleton";
import { Badge } from "../components/ui/Badge";
import { format } from "date-fns";

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
        <div className="grid gap-8 mt-6 md:grid-cols-2">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  if (isError || !media) {
    return <p className="text-destructive">Error loading media details.</p>;
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight truncate">{media.original_file_path}</h1>
        <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
          <span>Uploaded on {format(new Date(media.created_at), "PPP")}</span>
          <Badge variant="outline">{media.media_type}</Badge>
          <Badge variant="secondary">{media.status}</Badge>
        </div>
      </div>

      {/* Panels Section */}
      <div className="grid gap-8 md:grid-cols-2">
        <TranscriptionPanel mediaId={id} />
        <SummaryPanel mediaId={id} />
      </div>
    </div>
  );
};

export default MediaDetailPage;
