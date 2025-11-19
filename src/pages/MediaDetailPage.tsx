import { useState, useRef } from "react";
import { UserRole, SummaryStatus, TopicModelingStatus } from "@/types";
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
import { ptBR } from "date-fns/locale";
import { MediaType, MediaStatus, TranscriptionStatus } from "@/types";
import { MediaPlayer } from "@/features/media/components/MediaPlayer";
import { useTranscription } from "@/features/transcription/hooks/useTranscription";
import { TranscriptionPanel } from "@/features/transcription/components/TranscriptionPanel";
import { buildApiUrl } from "@/lib/api";
import { useSummary } from "@/features/summarization/hooks/useSummary";
import { useSentimentAnalysis } from "@/features/sentiment_analysis/hooks/useSentimentAnalysis";
import { useTopicModeling } from "@/features/topic_modeling/hooks/useTopicModeling";
import {
  CalendarDays,
  HardDrive,
  Shield,
  Sparkles,
  CheckCircle2,
  Loader2,
  AlertTriangle,
  Info,
  RefreshCw,
} from "lucide-react";

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

  const { data: media, isLoading, isError } = useMediaDetail(id);
  const reprocessMutation = useReprocessMedia();
  const { data: summaryData } = useSummary(id ?? "");
  const { data: sentimentData } = useSentimentAnalysis(id ?? "");
  const { data: topicData } = useTopicModeling(id ?? "");

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
    return <p className="text-destructive">Não foi possível carregar os detalhes da mídia.</p>;
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

  const formattedDate = format(new Date(media.created_at), "dd 'de' MMMM 'de' yyyy 'às' HH:mm", { locale: ptBR });
  const displayName = media.original_file_path?.split("/").pop() || media.original_file_path;

  const statusToken = (status?: string | null) => {
    switch (status) {
      case MediaStatus.COMPLETED:
      case SummaryStatus.COMPLETED:
      case TranscriptionStatus.COMPLETED:
      case TopicModelingStatus.COMPLETED:
      case "COMPLETED":
        return { label: "Concluído", badge: "bg-emerald-500/10 text-emerald-600", icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" /> };
      case MediaStatus.PROCESSING:
      case SummaryStatus.PROCESSING:
      case TranscriptionStatus.PROCESSING:
      case TopicModelingStatus.PROCESSING:
      case "PROCESSING":
        return { label: "Processando", badge: "bg-amber-500/10 text-amber-600", icon: <Loader2 className="h-4 w-4 animate-spin text-amber-500" /> };
      case MediaStatus.FAILED:
      case SummaryStatus.FAILED:
      case TranscriptionStatus.FAILED:
      case TopicModelingStatus.FAILED:
      case "FAILED":
        return { label: "Falhou", badge: "bg-red-500/10 text-red-600", icon: <AlertTriangle className="h-4 w-4 text-red-500" /> };
      case MediaStatus.PENDING:
      case SummaryStatus.PENDING:
      case TranscriptionStatus.PENDING:
      case TopicModelingStatus.PENDING:
      default:
        return { label: "Aguardando", badge: "bg-muted text-muted-foreground", icon: <Loader2 className="h-4 w-4 text-muted-foreground" /> };
    }
  };

  const sentimentStatus = sentimentData ? "COMPLETED" : media.status === MediaStatus.FAILED ? "FAILED" : media.status === MediaStatus.PROCESSING ? "PROCESSING" : "PENDING";
  const topicStatus = topicData?.status ?? (media.status === MediaStatus.COMPLETED ? TopicModelingStatus.PENDING : media.status);

  const pipelineSteps = [
    { key: "upload", label: "Upload", status: media.status, description: "Arquivo recebido e salvo" },
    { key: "transcription", label: "Transcrição", status: transcriptionData?.status ?? TranscriptionStatus.PENDING, description: "Conversão de áudio/vídeo em texto" },
    { key: "summary", label: "Resumo", status: summaryData?.status ?? SummaryStatus.PENDING, description: "Síntese inteligente do conteúdo" },
    { key: "sentiment", label: "Sentimento", status: sentimentStatus, description: "Tom emocional identificado" },
    { key: "topics", label: "Tópicos", status: topicStatus ?? TopicModelingStatus.PENDING, description: "Assuntos predominantes" },
  ];

  const metadataCards = [
    {
      label: "Armazenamento",
      value: media.storage_provider ?? "Não informado",
      icon: <HardDrive className="h-4 w-4" />,
    },
    {
      label: "Pipeline configurado",
      value: media.processing_pipeline?.join(" → ") ?? "Automático conforme tipo de mídia",
      icon: <Sparkles className="h-4 w-4" />,
    },
    {
      label: "ID da mídia",
      value: media.id,
      icon: <Info className="h-4 w-4" />,
    },
    {
      label: "Tamanho",
      value: media.file_size_mb ? `${media.file_size_mb.toFixed(2)} MB` : "—",
      icon: <Shield className="h-4 w-4" />,
    },
  ];

  const providerList = [
    { label: "Transcrição", value: media.transcription_provider },
    { label: "Resumo", value: media.summarization_provider },
    { label: "Sentimento", value: media.sentiment_provider },
    { label: "Tópicos", value: media.topic_modeling_provider },
  ];

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-border/60 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-6 text-white shadow-xl">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-white/70">Detalhes da mídia</p>
            <h1 className="text-3xl font-semibold leading-tight">{displayName}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-white/80">
              <span className="inline-flex items-center gap-1">
                <CalendarDays className="h-3.5 w-3.5" /> {formattedDate}
              </span>
              <Badge variant="outline" className="border-white/40 text-white">
                {media.media_type}
              </Badge>
              <Badge className={statusToken(media.status).badge}>{statusToken(media.status).label}</Badge>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 text-sm text-white/80">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-emerald-300" />
              <span>{media.storage_provider ?? "Storage padrão"}</span>
            </div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-300" />
              <span>{media.processing_pipeline?.length ? `${media.processing_pipeline.length} etapas configuradas` : "Pipeline automático"}</span>
            </div>
            {user?.role === UserRole.ADMIN && media.status === MediaStatus.FAILED && (
              <Button
                onClick={handleReprocess}
                disabled={reprocessMutation.isPending}
                variant="secondary"
                size="sm"
                className="mt-2"
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
        {media.status === MediaStatus.FAILED && media.error_message && (
          <div className="mt-4 rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm">
            <p className="font-semibold text-red-200">Falha no processamento</p>
            <p className="text-red-100/80">{media.error_message}</p>
          </div>
        )}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metadataCards.map((item) => (
          <Card key={item.label} className="border border-border/60">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="text-primary">{item.icon}</span>
                {item.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-base font-medium text-foreground">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Status do pipeline</CardTitle>
            <CardDescription>
              Acompanhamento das principais etapas de processamento alinhadas com o backend.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {pipelineSteps.map((step) => {
              const token = statusToken(step.status);
              return (
                <div key={step.key} className="flex items-start justify-between gap-3 rounded-xl border border-border/60 p-3">
                  <div>
                    <div className="flex items-center gap-2 text-sm font-medium">
                      {token.icon}
                      <span>{step.label}</span>
                      <Badge className={token.badge}>{token.label}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{step.description}</p>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Provedores vinculados</CardTitle>
            <CardDescription>Origem de cada etapa do pipeline.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {providerList.map((provider) => (
              <div key={provider.label} className="rounded-xl border border-border/50 p-3 text-sm">
                <p className="text-muted-foreground">{provider.label}</p>
                <p className="font-medium text-foreground">{provider.value ?? "Automático"}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Pré-visualização</CardTitle>
          <CardDescription className="text-sm text-muted-foreground">
            Local: {media.storage_provider ?? "Desconhecido"}
            {media.original_file_path && <> · {media.original_file_path}</>}
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
              Prévia indisponível para este tipo de arquivo.
            </p>
          )}
          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span>Armazenamento: {media.storage_provider ?? "—"}</span>
            {media.original_file_path && <span className="truncate">Caminho: {media.original_file_path}</span>}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          {isPlayable && (
            <InteractiveTranscriptionPanel mediaId={id} currentTime={currentTime} onSeek={handleSeek} />
          )}
          {!isPlayable && isTextMedia && <TranscriptionPanel mediaId={id} />}
          {!isPlayable && !isTextMedia && (
            <p className="py-16 text-center text-muted-foreground">
              Ainda não há transcrição disponível para este formato.
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
