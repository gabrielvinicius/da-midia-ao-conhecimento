import { useState, useRef } from "react";
import { UserRole } from "@/types";
import { useParams } from "react-router-dom";
import { useMediaByIdQuery, useTextAnalysisByMediaIdQuery } from "@/hooks/useQueries";
import { useReprocessMediaCommand } from "@/hooks/useCommands";
import { InteractiveTranscriptionPanel } from "@/features/transcription/components/InteractiveTranscriptionPanel";
import { TopicModelingResultPanel } from "@/features/topic_modeling/components/TopicModelingResultPanel";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { MagicSurface } from "@/components/ui/MagicSurface";
import { useAuth } from "@/contexts/AuthContext";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { MediaStatus, TranscriptionStatus, MediaType } from "@/types";
import { cn } from "@/lib/utils";
import { MediaPlayer } from "@/features/media/components/MediaPlayer";
import { useTranscription } from "@/features/transcription/hooks/useTranscription";
import { TranscriptionPanel } from "@/features/transcription/components/TranscriptionPanel";
import { buildApiUrl } from "@/lib/api";
import { SummaryPanel } from "@/features/summarization/components/SummaryPanel";
import authService from "@/services/auth.service";
import { PredictiveInsight } from "@/components/PredictiveInsight";
import { ProcessingTrace } from "@/components/ProcessingTrace";

import {
  CalendarDays,
  HardDrive,
  Shield,
  Loader2,
  Info,
  RefreshCw,
  Languages,
  FileText,
} from "lucide-react";

type PipelineStep = {
  key: string;
  label: string;
  status?: string | null;
  description: string;
};

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
    return <p className="text-destructive">Nenhum ID de mídia informado.</p>;
  }

  const { data: media, isLoading, isError } = useMediaByIdQuery(id);
  const reprocessMutation = useReprocessMediaCommand();
  const { data: textAnalysis } = useTextAnalysisByMediaIdQuery(id);

  const handleReprocess = () => {
    if (media) {
      reprocessMutation.mutate({ mediaId: media.id });
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
  const token = authService.getToken();
  const streamUrl = buildApiUrl(`/media/${media.id}/stream${token ? `?token=${token}` : ''}`);

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
  
  const summaryConfigured = Boolean(media.summarization_provider) || media.status === MediaStatus.COMPLETED;
  const topicsConfigured = Boolean(media.topic_modeling_provider) || media.status === MediaStatus.COMPLETED;

  const computeStageStatus = (primary?: string | null, configured = true): string => {
    if (!configured) return "SKIPPED";
    if (primary && primary !== TranscriptionStatus.PENDING) {
      return primary;
    }
    if (primary === TranscriptionStatus.FAILED) {
      return "FAILED";
    }
    if (primary === TranscriptionStatus.PROCESSING) {
      return "PROCESSING";
    }
    if (media.status === MediaStatus.FAILED) {
      return MediaStatus.FAILED;
    }
    if (media.status === MediaStatus.PROCESSING) {
      return MediaStatus.PROCESSING;
    }
    if (media.status === MediaStatus.COMPLETED) {
      return MediaStatus.COMPLETED;
    }
    if (media.status === MediaStatus.UPLOADED) {
      return MediaStatus.UPLOADED;
    }
    return "PENDING";
  };

  const uploadStageStatus = media.status === MediaStatus.FAILED ? MediaStatus.FAILED : MediaStatus.COMPLETED;
  const videoStageStatus = media.media_type === MediaType.VIDEO ? computeStageStatus(media.status, true) : "SKIPPED";
  const transcriptionStageStatus = computeStageStatus(transcriptionData?.status ?? (isTextMedia ? transcriptionData?.status : undefined), true);
  const analysisStage = textAnalysis ? MediaStatus.COMPLETED : undefined;
  const summaryStageStatus = computeStageStatus(analysisStage, summaryConfigured);
  const topicStageStatus = computeStageStatus(analysisStage, topicsConfigured);

  const statusToken = (status?: string | null) => {
    switch (status) {
      case MediaStatus.COMPLETED:
      case TranscriptionStatus.COMPLETED:
      case "COMPLETED":
        return { label: "Concluído", badge: "bg-emerald-500/10 text-emerald-600", icon: <Loader2 className="h-4 w-4 text-emerald-500" /> };
      case MediaStatus.PROCESSING:
      case TranscriptionStatus.PROCESSING:
      case "PROCESSING":
        return { label: "Processando", badge: "bg-amber-500/10 text-amber-600", icon: <Loader2 className="h-4 w-4 animate-spin text-amber-500" /> };
      case MediaStatus.FAILED:
      case TranscriptionStatus.FAILED:
      case "FAILED":
        return { label: "Falhou", badge: "bg-red-500/10 text-red-600", icon: <Info className="h-4 w-4 text-red-500" /> };
      case MediaStatus.PENDING:
      case TranscriptionStatus.PENDING:
      case MediaStatus.UPLOADED:
      case "UPLOADED":
        return { label: "Aguardando", badge: "bg-muted text-muted-foreground", icon: <Loader2 className="h-4 w-4 text-muted-foreground" /> };
      case "SKIPPED":
        return { label: "Não configurado", badge: "bg-muted text-muted-foreground", icon: <Info className="h-4 w-4 text-muted-foreground" /> };
      default:
        return { label: "Aguardando", badge: "bg-muted text-muted-foreground", icon: <Loader2 className="h-4 w-4 text-muted-foreground" /> };
    }
  };

  const pipelineSteps: PipelineStep[] = [];

  pipelineSteps.push({
    key: "upload",
    label: "Upload e validação",
    status: media.status === MediaStatus.FAILED ? MediaStatus.FAILED : uploadStageStatus,
    description: "Arquivo recebido, validado e armazenado com segurança.",
  });

  if (media.media_type === MediaType.VIDEO) {
    pipelineSteps.push({
      key: "video",
      label: "Processamento de vídeo",
      status: videoStageStatus,
      description: "Extração de áudio, frames e metadados necessários para análise.",
    });
  }

  pipelineSteps.push({
    key: "transcription",
    label: isTextMedia ? "Extração do documento" : "Transcrição Neural",
    status: transcriptionStageStatus,
    description: isTextMedia
      ? "Conversão de arquivos de texto em conteúdo bruto estruturado."
      : "Conversão do áudio em texto com identificação de locutores.",
  });

  pipelineSteps.push({
    key: "topics",
    label: "Descoberta de Tópicos",
    status: topicStageStatus,
    description: topicStageStatus === MediaStatus.COMPLETED
      ? "Temas e conceitos extraídos com sucesso."
      : topicStageStatus === MediaStatus.PROCESSING
      ? "Mapeando a topografia semântica..."
      : "Aguardando processamento textual.",
  });

  pipelineSteps.push({
    key: "summary",
    label: "Síntese Interpretativa",
    status: summaryStageStatus,
    description: summaryStageStatus === MediaStatus.COMPLETED
      ? "Artigo analítico consolidado."
      : summaryStageStatus === MediaStatus.PROCESSING
      ? "Gerando narrativa multimodal..."
      : "Aguardando descoberta de tópicos.",
  });

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
              <Badge className={statusToken(media.status).badge}>{statusToken(media.status).label}</Badge>
              
              {/* Level 6.0 Visual Observability */}
              <ProcessingTrace media={media} analysis={textAnalysis} />
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
              {isPlayable ? (
                <MediaPlayer
                  src={streamUrl}
                  mediaType={media.media_type as MediaType.AUDIO | MediaType.VIDEO}
                  playerRef={playerRef}
                  onTimeUpdate={setCurrentTime}
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
          <SummaryPanel mediaId={id} mediaStatus={media.status} />

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
            isEnabled={media.status === MediaStatus.UPLOADED || media.status === MediaStatus.PROCESSING} 
          />

          {/* Topics Index */}
          <TopicModelingResultPanel mediaId={id} mediaStatus={media.status} />

          {/* Metadata / Pipeline Status */}
          <Card className="border border-slate-200 bg-white shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-50">
              <CardTitle className="text-xs font-bold uppercase tracking-widest text-slate-400">Dados do Sistema</CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4 text-sm">
              <div className="flex justify-between py-1.5">
                <span className="text-muted-foreground flex items-center gap-2"><FileText className="h-3.5 w-3.5"/> Nome</span>
                <span className="font-medium truncate max-w-[150px] text-slate-700" title={media.filename || media.id}>{media.filename || media.id}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-muted-foreground flex items-center gap-2"><Shield className="h-3.5 w-3.5"/> Tamanho</span>
                <span className="font-medium text-slate-700">{formattedFileSize}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-muted-foreground flex items-center gap-2"><HardDrive className="h-3.5 w-3.5"/> Storage</span>
                <span className="font-medium text-slate-700">{media.storage_provider ?? "Local"}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-muted-foreground flex items-center gap-2"><Languages className="h-3.5 w-3.5"/> Idioma</span>
                <span className="font-medium text-slate-700">{languageLabel}</span>
              </div>
              
              <div className="pt-4 border-t border-slate-50">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4">Etapas de Processamento</p>
                <div className="space-y-3">
                  {pipelineSteps.map((step) => {
                    const token = statusToken(step.status);
                    return (
                      <div key={step.key} className="group flex items-start justify-between gap-4">
                        <div className="flex items-center gap-2">
                          <div className="mt-0.5">{token.icon}</div>
                          <div className="flex flex-col">
                            <span className="text-xs font-medium text-slate-700 leading-none">{step.label}</span>
                          </div>
                        </div>
                        <Badge className={cn("text-[9px] font-bold px-1.5 h-4 min-w-[70px] justify-center uppercase tracking-tighter", token.badge)}>
                          {token.label}
                        </Badge>
                      </div>
                    );
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

type TextPreviewProps = {
  transcription: string;
  isLoading: boolean;
  isError: boolean;
  status?: TranscriptionStatus;
};

const TextPreview = ({ transcription, isLoading, isError, status }: TextPreviewProps) => {
  const statusMap: Record<string, string> = {
    [TranscriptionStatus.COMPLETED]: "Concluído",
    [TranscriptionStatus.PROCESSING]: "Processando",
    [TranscriptionStatus.FAILED]: "Falhou",
    [TranscriptionStatus.PENDING]: "Pendente",
  };

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
  const statusLabel = status ? statusMap[status] ?? status : "";

  return (
    <div className="space-y-2">
      <pre className="max-h-60 overflow-y-auto whitespace-pre-wrap rounded-md bg-muted/40 p-3 text-sm">
        {truncated}
      </pre>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-2">
          <Badge variant="secondary" className="uppercase tracking-wide">
            {statusLabel || "Transcrito"}
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

export default MediaDetailPage;
