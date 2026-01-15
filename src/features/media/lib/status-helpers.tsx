import { MediaStatus, TranscriptionStatus, MediaType } from "@/types";
import { Loader2, Info } from "lucide-react";
import { ReactNode } from "react";

export const computeStageStatus = (
  mediaStatus: MediaStatus,
  mediaType: MediaType,
  primaryStatus?: string | null,
  configured: boolean = true
): string => {
  if (!configured) return "SKIPPED";
  if (primaryStatus && primaryStatus !== TranscriptionStatus.PENDING) {
    return primaryStatus;
  }
  if (primaryStatus === TranscriptionStatus.FAILED) {
    return "FAILED";
  }
  if (primaryStatus === TranscriptionStatus.PROCESSING) {
    return "PROCESSING";
  }
  if (mediaStatus === MediaStatus.FAILED) {
    return MediaStatus.FAILED;
  }
  if (mediaStatus === MediaStatus.PROCESSING) {
    return MediaStatus.PROCESSING;
  }
  if (mediaStatus === MediaStatus.COMPLETED) {
    return MediaStatus.COMPLETED;
  }
  if (mediaStatus === MediaStatus.UPLOADED) {
    return MediaStatus.UPLOADED;
  }
  return "PENDING";
};

export const getStatusToken = (status?: string | null): { label: string; badge: string; icon: ReactNode } => {
  switch (status) {
    case MediaStatus.COMPLETED:
    case TranscriptionStatus.COMPLETED:
    case "COMPLETED":
      return { 
        label: "Concluído", 
        badge: "bg-emerald-500/10 text-emerald-600", 
        icon: <Loader2 className="h-4 w-4 text-emerald-500" /> 
      };
    case MediaStatus.PROCESSING:
    case TranscriptionStatus.PROCESSING:
    case "PROCESSING":
      return { 
        label: "Processando", 
        badge: "bg-amber-500/10 text-amber-600", 
        icon: <Loader2 className="h-4 w-4 animate-spin text-amber-500" /> 
      };
    case MediaStatus.FAILED:
    case TranscriptionStatus.FAILED:
    case "FAILED":
      return { 
        label: "Falhou", 
        badge: "bg-red-500/10 text-red-600", 
        icon: <Info className="h-4 w-4 text-red-500" /> 
      };
    case MediaStatus.PENDING:
    case TranscriptionStatus.PENDING:
    case MediaStatus.UPLOADED:
    case "UPLOADED":
      return { 
        label: "Aguardando", 
        badge: "bg-muted text-muted-foreground", 
        icon: <Loader2 className="h-4 w-4 text-muted-foreground" /> 
      };
    case "SKIPPED":
      return { 
        label: "Não configurado", 
        badge: "bg-muted text-muted-foreground", 
        icon: <Info className="h-4 w-4 text-muted-foreground" /> 
      };
    default:
      return { 
        label: "Aguardando", 
        badge: "bg-muted text-muted-foreground", 
        icon: <Loader2 className="h-4 w-4 text-muted-foreground" /> 
      };
  }
};
