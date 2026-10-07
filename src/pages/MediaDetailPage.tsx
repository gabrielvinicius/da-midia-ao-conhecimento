import { useState, useRef } from "react";
import { UserRole } from "@/types";
import { useParams, useSearchParams } from "react-router-dom";
import { useMediaByIdQuery } from "@/features/media/hooks/useMediaQueries";
import { useTextAnalysisByMediaIdQuery } from "@/features/summarization/hooks/useAnalysisQuery";
import { useReprocessMediaMutation } from "@/features/media/hooks/useMediaMutations";
import { InteractiveTranscriptionPanel } from "@/features/transcription/components/InteractiveTranscriptionPanel";
import { TopicModelingResultPanel } from "@/features/topic_modeling/components/TopicModelingResultPanel";
import { SentimentResultPanel } from "@/features/sentiment_analysis/components/SentimentResultPanel";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { MagicSurface } from "@/components/ui/MagicSurface";
import { useAuth } from "@/contexts/AuthContext";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { MediaStatus, MediaType, isInProgress } from "@/types";
import { MediaPlayer } from "@/features/media/components/MediaPlayer";
import { useTranscription } from "@/features/transcription/hooks/useTranscription";
import { TranscriptionPanel } from "@/features/transcription/components/TranscriptionPanel";
import { buildApiUrl } from "@/lib/api";
import { SummaryPanel } from "@/features/summarization/components/SummaryPanel";
import { useQuery } from "@tanstack/react-query";
import { requestScopedToken } from "@/features/authentication/api/scopedToken";
import { PredictiveInsight } from "@/components/PredictiveInsight";
import { ProcessingTrace } from "@/components/ProcessingTrace";
import { getStatusToken } from "@/features/media/lib/status-helpers";
import { mediaPipelineSteps } from "@/features/media/lib/pipelineSteps";
import { MediaSystemCard } from "@/features/media/components/MediaSystemCard";
import { TextPreview } from "@/features/media/components/TextPreview";

import {
  CalendarDays,
  Loader2,
  Info,
  RefreshCw,
} from "lucide-react";

const MediaDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  // ?t=SEGUNDOS: a busca abre a mídia no momento do trecho encontrado.
  const [searchParams] = useSearchParams();
  const startAt = Number(searchParams.get("t")) || undefined;
  const { user } = useAuth();
  const playerRef = useRef<HTMLMediaElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const {
    data: transcriptionData,
    isLoading: isTranscriptionLoading,
    isError: isTranscriptionError,
  } = useTranscription(id ?? "");

  // Hooks sempre na mesma ordem: o retorno antecipado vem depois deles.
  const { data: media, isLoading, isError } = useMediaByIdQuery(id ?? "");
  const reprocessMutation = useReprocessMediaMutation();
  const { data: textAnalysis } = useTextAnalysisByMediaIdQuery(id ?? "");
  const isPlayableMedia = media?.media_type === MediaType.AUDIO || media?.media_type === MediaType.VIDEO;
  // Token só desta mídia, válido por horas: a URL do vídeo não muda no meio
  // da reprodução (antes, o token de acesso na URL expirava em 30 min).
  const { data: streamToken } = useQuery({
    queryKey: ["stream-token", id],
    queryFn: () => requestScopedToken("media_stream", id),
    enabled: Boolean(id && isPlayableMedia),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  if (!id) {
    return <p className="text-destructive">Nenhum ID de mídia informado.</p>;
  }

  const handleReprocess = () => {
    if (media) {
      reprocessMutation.mutate(media.id);
    }
  };

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
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !media) {
    return <p className="text-destructive">Não foi possível carregar os detalhes da mídia.</p>;
  }

  const isPlayable = media.media_type === MediaType.AUDIO || media.media_type === MediaType.VIDEO;
  const isTextMedia = media.media_type === MediaType.TEXT;
  const streamUrl = streamToken
    ? buildApiUrl(`/media/${media.id}/stream?token=${encodeURIComponent(streamToken)}`)
    : "";

  const handleSeek = (time: number) => {
    if (playerRef.current) {
      playerRef.current.currentTime = time;
      playerRef.current.play();
    }
  };

  const formattedDate = format(new Date(media.created_at), "dd 'de' MMMM 'de' yyyy 'às' HH:mm", { locale: ptBR });
  const displayName = media.filename || media.id;
  const rawFileSize = media.size ?? null;
  const fileSizeMb = rawFileSize ? rawFileSize / (1024 * 1024) : undefined;
  const formattedFileSize = fileSizeMb ? `${fileSizeMb.toFixed(2)} MB` : "Indisponível";
  const derivedLanguage = media.language || transcriptionData?.language;
  const languageLabel = derivedLanguage ? derivedLanguage.toUpperCase() : "Indefinido";
  
  return (
    <div className="space-y-6 h-full flex flex-col pb-12">
      {/* Header Section */}
      <MagicSurface title="Detalhes da mídia" description="Análise completa do conhecimento extraído.">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold leading-tight text-slate-900 break-words">{displayName}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <CalendarDays className="h-3.5 w-3.5" /> {formattedDate}
              </span>
              <Badge variant="secondary" className="bg-white text-slate-900 capitalize">
                {media.media_type}
              </Badge>
              <Badge className={getStatusToken(media.status).badge}>{getStatusToken(media.status).label}</Badge>
              
              <ProcessingTrace media={media} analysis={textAnalysis} transcriptionStatus={transcriptionData?.status} />
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 text-sm text-muted-foreground">
            <div className="flex items-center gap-3">
               {(user?.role === UserRole.ADMIN || media.user_id === user?.id) && media.status === MediaStatus.FAILED && (
                <Button
                  onClick={handleReprocess}
                  disabled={reprocessMutation.isPending}
                  variant="outline"
                  size="sm"
                >
                  {reprocessMutation.isPending ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Reprocessando...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <RefreshCw className="h-4 w-4" />
                      Reprocessar
                    </span>
                  )}
                </Button>
              )}
            </div>
          </div>
        </div>
        {media.status === MediaStatus.FAILED && media.error_message && (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <p className="font-semibold">Falha no processamento</p>
            <p>{media.error_message}</p>
          </div>
        )}
      </MagicSurface>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Player & Interpretative Summary */}
        <div className="lg:col-span-2 space-y-8">
          {/* Media Player Card */}
          <Card className="border-none bg-black/5 overflow-hidden shadow-sm">
            <CardContent className="p-0">
              {isPlayable && !streamUrl ? (
                <Skeleton className="aspect-video w-full" />
              ) : isPlayable ? (
                <MediaPlayer
                  src={streamUrl}
                  mediaType={media.media_type as MediaType.AUDIO | MediaType.VIDEO}
                  playerRef={playerRef}
                  onTimeUpdate={setCurrentTime}
                  startAt={startAt}
                />
              ) : isTextMedia ? (
                  <div className="p-6">
                    <TextPreview
                      isLoading={isTranscriptionLoading}
                      isError={isTranscriptionError}
                      transcription={transcriptionData?.text || ""}
                      status={transcriptionData?.status}
                    />
                  </div>
              ) : (
                <div className="p-12 text-center text-muted-foreground">
                  <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>Prévia indisponível para este tipo de arquivo.</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* MAIN INSIGHT: Interpretative Article */}
          <SummaryPanel mediaId={id} mediaStatus={media.status} onSeek={isPlayable ? handleSeek : undefined} />

          {/* Interactive Transcription */}
          <div className="min-h-[400px]">
             {isPlayable && (
              <InteractiveTranscriptionPanel mediaId={id} currentTime={currentTime} onSeek={handleSeek} />
            )}
            {!isPlayable && isTextMedia && <TranscriptionPanel mediaId={id} />}
          </div>
        </div>

        {/* Right Column: Index & Technical Meta */}
        <div className="space-y-6">
          {/* Predictive Insight */}
          <PredictiveInsight 
            mediaId={id} 
            isEnabled={media.status === MediaStatus.UPLOADED || isInProgress(media.status)} 
          />

          {/* Topics Index */}
          <TopicModelingResultPanel mediaId={id} mediaStatus={media.status} />

          {/* Tom predominante (análise de sentimento) */}
          <SentimentResultPanel mediaId={id} mediaStatus={media.status} />

          <MediaSystemCard
            filename={displayName}
            fileSize={formattedFileSize}
            storage={media.storage_provider ?? "Local"}
            language={languageLabel}
            steps={mediaPipelineSteps(media, transcriptionData?.status, textAnalysis)}
          />
        </div>
      </div>
    </div>
  );
};

export default MediaDetailPage;
