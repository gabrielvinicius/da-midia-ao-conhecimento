import { useState, useRef } from "react";
import { UserRole } from "@/types";
import { useParams } from "react-router-dom";
import { useMediaDetail, useReprocessMedia } from "../features/media/hooks/useMedia";
import { InteractiveTranscriptionPanel } from "../features/transcription/components/InteractiveTranscriptionPanel";
import { SummaryPanel } from "../features/summarization/components/SummaryPanel";
import { SentimentResultPanel } from "@/features/sentiment_analysis/components/SentimentResultPanel";
import { TopicModelingResultPanel } from "@/features/topic_modeling/components/TopicModelingResultPanel"; // Re-enable v2 Feature
import { Skeleton } from "../components/ui/Skeleton";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { useAuth } from "../contexts/AuthContext";
import { format } from "date-fns";
import { MediaType, MediaStatus, TranscriptionStatus } from "@/types";
import { MediaPlayer } from "@/features/media/components/MediaPlayer";
import { useTranscription } from "@/features/transcription/hooks/useTranscription";
import { TranscriptionPanel } from "@/features/transcription/components/TranscriptionPanel";
import { buildApiUrl } from "@/lib/api";

const MediaDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const playerRef = useRef<HTMLMediaElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const {
    data: transcriptionData,
    isLoading: isTranscriptionLoading,
    isError: isTranscriptionError,
  } = useTranscription(id ?? "");

  if (!id) {
    return <p>No media ID provided.</p>;
  }

  const { data: media, isLoading, isError } = useMediaDetail(id);
  const reprocessMutation = useReprocessMedia();

  const handleReprocess = () => {
    if (media) {
      reprocessMutation.mutate({ mediaId: media.id });
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
  const isTextMedia = media.media_type === MediaType.TEXT;
  const streamUrl = buildApiUrl(`/media/${media.id}/stream`);

  const handleSeek = (time: number) => {
    if (playerRef.current) {
      playerRef.current.currentTime = time;
      playerRef.current.play();
    }
  };

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
          {user?.role === UserRole.ADMIN && media.status === MediaStatus.FAILED && (
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

      <Card>
        <CardHeader>
          <CardTitle>Media Playback</CardTitle>
          <CardDescription className="text-sm text-muted-foreground">
            Storage: {media.storage_provider}
            {media.original_file_path && (
              <> · {media.original_file_path}</>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isPlayable ? (
            <MediaPlayer
              src={streamUrl}
              mediaType={media.media_type as MediaType.AUDIO | MediaType.VIDEO}
              playerRef={playerRef}
              onTimeUpdate={setCurrentTime}
            />
          ) : isTextMedia ? (
            <TextPreview
              isLoading={isTranscriptionLoading}
              isError={isTranscriptionError}
              transcription={transcriptionData?.result?.text || transcriptionData?.text || ""}
              status={transcriptionData?.status}
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              Pré-visualização indisponível para este tipo de arquivo.
            </p>
          )}
          <div className="text-xs text-muted-foreground flex justify-between flex-wrap gap-2">
            <span>Provider: {media.storage_provider}</span>
            {media.original_file_path && <span className="truncate">Path: {media.original_file_path}</span>}
          </div>
        </CardContent>
      </Card>

      {/* Main Content Layout */}
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          {isPlayable && (
            <InteractiveTranscriptionPanel
              mediaId={id}
              currentTime={currentTime}
              onSeek={handleSeek}
            />
          )}
          {!isPlayable && isTextMedia && (
            <TranscriptionPanel mediaId={id} />
          )}
          {!isPlayable && !isTextMedia && (
            <p className="text-center text-muted-foreground py-16">
              Ainda não há transcrição disponível para este tipo de arquivo.
            </p>
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

type TextPreviewProps = {
  transcription: string;
  isLoading: boolean;
  isError: boolean;
  status?: TranscriptionStatus;
};

const TextPreview = ({ transcription, isLoading, isError, status }: TextPreviewProps) => {
  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }

  if (isError) {
    return <p className="text-sm text-destructive">Erro ao carregar a transcrição.</p>;
  }

  if (!transcription) {
    return (
      <p className="text-sm text-muted-foreground">
        Estamos processando o texto deste documento. Volte em instantes para visualizar a transcrição.
      </p>
    );
  }

  const truncated = transcription.length > 800 ? `${transcription.slice(0, 800)}…` : transcription;
  const statusLabel = status ? status.toLowerCase() : "";

  return (
    <div className="space-y-2">
      <pre className="max-h-60 overflow-y-auto whitespace-pre-wrap rounded-md bg-muted/40 p-3 text-sm">
        {truncated}
      </pre>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-2">
          <Badge variant="secondary" className="uppercase tracking-wide">
            {statusLabel || "transcrito"}
          </Badge>
          Prévia em texto bruto
        </span>
        <span>
          Exibindo {Math.min(truncated.length, transcription.length)} de {transcription.length} caracteres
        </span>
      </div>
    </div>
  );
};
