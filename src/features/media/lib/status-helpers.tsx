import { MediaStatus, TranscriptionStatus, MediaType } from "@/types";
import { CheckCircle2, Loader2, Info } from "lucide-react";
import { ReactNode } from "react";

/** Estado de uma etapa: o próprio, se já começou; senão, o da mídia. */
export const computeStageStatus = (
  mediaStatus: MediaStatus,
  _mediaType: MediaType,
  primaryStatus?: string | null,
  configured: boolean = true
): string => {
  if (!configured) return "SKIPPED";
  if (primaryStatus && primaryStatus !== TranscriptionStatus.PENDING) return primaryStatus;
  return mediaStatus ?? "PENDING";
};

export const getStatusToken = (status?: string | null): { label: string; badge: string; icon: ReactNode } => {
  switch (status) {
    case MediaStatus.COMPLETED:
    case TranscriptionStatus.COMPLETED:
    case "COMPLETED":
      return { 
        label: "Concluído", 
        badge: "bg-emerald-500/10 text-emerald-600", 
        icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" /> 
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
