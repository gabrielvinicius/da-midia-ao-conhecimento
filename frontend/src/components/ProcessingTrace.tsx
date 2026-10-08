import { Cpu } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Media, TextAnalysisResponse, isInProgress } from "@/types";
import { cn } from "@/lib/utils";
import { formatSeconds, taskLabel } from "@/lib/processingLabels";
import { mediaPipelineSteps } from "@/features/media/lib/pipelineSteps";
import { getStatusToken } from "@/features/media/lib/status-helpers";
import { summarySourceLabel } from "@/features/summarization/components/SummaryPanel";

type Props = {
  media: Media;
  analysis?: TextAnalysisResponse | null;
  transcriptionStatus?: string | null;
};

/**
 * O que o servidor registrou sobre o processamento desta mídia: o estado de
 * cada etapa, quanto tempo cada etapa da análise levou, o dispositivo usado e
 * de onde veio o resumo. Nada aqui é estimado ou simulado.
 */
export const ProcessingTrace = ({ media, analysis, transcriptionStatus }: Props) => {
  const steps = mediaPipelineSteps(media, transcriptionStatus, analysis);
  const diagnostics = (analysis?.diagnostics ?? {}) as Record<string, unknown>;
  const outcomes = (diagnostics.steps ?? {}) as Record<string, string>;
  const seconds = (diagnostics.step_seconds ?? {}) as Record<string, number>;
  const analysisSteps = Object.keys(seconds);
  const source = summarySourceLabel(diagnostics.summary_source);
  const device = typeof diagnostics.hardware_target === "string" ? diagnostics.hardware_target : null;
  const precision = typeof diagnostics.compute_type === "string" ? diagnostics.compute_type : null;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-muted-foreground hover:text-primary">
          <Cpu className={cn("h-3.5 w-3.5", isInProgress(media.status) && "text-amber-500 animate-pulse")} />
          <span className="text-[10px] uppercase tracking-wider font-bold">Detalhes do processamento</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[460px]">
        <DialogHeader>
          <DialogTitle>Detalhes do processamento</DialogTitle>
          <DialogDescription>O que o servidor registrou para esta mídia.</DialogDescription>
        </DialogHeader>

        <ul className="space-y-2 text-sm">
          {steps.map((step) => {
            const token = getStatusToken(step.status);
            return (
              <li key={step.key} className="flex items-center justify-between gap-4">
                <span className="flex items-center gap-2">{token.icon}{step.label}</span>
                <Badge className={cn("text-[10px] uppercase", token.badge)}>{token.label}</Badge>
              </li>
            );
          })}
        </ul>

        {analysisSteps.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Etapas da análise</p>
            <ul className="space-y-1 text-xs">
              {analysisSteps.map((step) => (
                <li key={step} className="flex justify-between gap-4">
                  <span className={outcomes[step]?.startsWith("failed") ? "text-destructive" : undefined}>
                    {taskLabel(`analysis.${step}`)}
                    {outcomes[step]?.startsWith("failed") && " (falhou)"}
                  </span>
                  <span className="font-mono text-muted-foreground">{formatSeconds(seconds[step])}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {(device || source) && (
          <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
            {device && (
              <>
                <dt className="text-muted-foreground">Dispositivo</dt>
                <dd>{device.toUpperCase()}{precision ? ` (${precision})` : ""}</dd>
              </>
            )}
            {source && (
              <>
                <dt className="text-muted-foreground">Resumo</dt>
                <dd>{source}</dd>
              </>
            )}
          </dl>
        )}
      </DialogContent>
    </Dialog>
  );
};
