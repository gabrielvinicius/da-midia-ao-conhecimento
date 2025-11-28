import { useMemo } from "react";
import { useTranscription } from "../hooks/useTranscription";
import { Skeleton } from "../../../components/ui/Skeleton";
import { Badge } from "../../../components/ui/Badge";
import { MagicSurface } from "@/components/ui/MagicSurface";
import { MediaStatus, TranscriptionStatus } from "../../../types";
import { cn } from "@/lib/utils";
import { Sparkles, Activity, Languages } from "lucide-react";

interface TranscriptionPanelProps {
  mediaId: string;
}

export const TranscriptionPanel = ({ mediaId }: TranscriptionPanelProps) => {
  const { data: transcription, isLoading, isError } = useTranscription(mediaId);

  const heartbeat = useMemo(() => {
    if (!transcription) return "bg-muted";
    switch (transcription.status) {
      case TranscriptionStatus.COMPLETED:
        return "bg-emerald-500/40";
      case TranscriptionStatus.PROCESSING:
        return "bg-amber-500/40 animate-pulse";
      case TranscriptionStatus.FAILED:
        return "bg-red-500/40";
      default:
        return "bg-muted";
    }
  }, [transcription]);

  const stats = useMemo(() => {
    if (!transcription) return [];
    return [
      {
        label: "Idioma detectado",
        value: transcription.language?.toUpperCase() ?? "AUTO",
        icon: <Languages className="h-4 w-4 text-emerald-400" />,
      },
      {
        label: "Modelo",
        value: transcription.provider ?? "fastwhisper",
        icon: <Activity className="h-4 w-4 text-sky-400" />,
      },
      {
        label: "Segments",
        value: transcription.segments?.length ?? 0,
        icon: <Sparkles className="h-4 w-4 text-purple-400" />,
      },
    ];
  }, [transcription]);

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
      return (
        <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/40 p-4 text-sm text-muted-foreground">
          Aguardando o áudio ser enviado ao provedor. Assim que começar, você vê o progresso aqui em tempo real.
        </div>
      );
    }

    switch (transcription.status) {
      case TranscriptionStatus.PENDING:
      case TranscriptionStatus.PROCESSING:
        return (
          <div className="space-y-2 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">Processando transcrição...</p>
            <div className="flex gap-2 text-xs">
              <Skeleton className="h-2 w-12 rounded-full" />
              <Skeleton className="h-2 w-16 rounded-full" />
            </div>
            <p>Estamos convertendo o áudio em texto. Você receberá insights assim que concluirmos.</p>
          </div>
        );
      case TranscriptionStatus.COMPLETED:
        return (
          <div className="space-y-3">
            <div className="rounded-2xl bg-slate-900/50 px-4 py-3 text-sm leading-relaxed text-slate-100 shadow-inner shadow-black/40">
              {transcription.result?.text || transcription.text}
            </div>
            {transcription.segments && (
              <div className="grid gap-2 text-xs text-muted-foreground">
                {transcription.segments.slice(0, 3).map((segment, idx) => (
                  <div key={idx} className="flex justify-between rounded-lg border border-white/5 bg-slate-950/40 px-3 py-2">
                    <span className="font-medium text-slate-100">{segment.text}</span>
                    <span>{segment.start.toFixed(1)}s</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      case TranscriptionStatus.FAILED:
        return (
          <p className="text-destructive">
            Falha na transcrição: {transcription.error_message || "Erro desconhecido"}
          </p>
        );
      default:
        return <p className="text-muted-foreground">Status de transcrição desconhecido.</p>;
    }
  };

  return (
    <MagicSurface title="Transcrição" description="Atualizações em tempo real da engine de áudio">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs uppercase tracking-[0.3em] text-white/60">Status atual</p>
        <Badge className={cn("border-none px-4 py-1 text-xs", heartbeat)}>{transcription?.status ?? MediaStatus.UPLOADED}</Badge>
      </div>
      {stats.length > 0 && (
        <div className="mb-4 grid gap-3 rounded-2xl border border-white/5 bg-white/5 p-3 text-xs text-slate-200 sm:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.label} className="flex flex-col gap-1">
              <span className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-slate-400">
                {stat.icon}
                {stat.label}
              </span>
              <span className="text-sm font-semibold text-white">{stat.value}</span>
            </div>
          ))}
        </div>
      )}
      {renderContent()}
    </MagicSurface>
  );
};
