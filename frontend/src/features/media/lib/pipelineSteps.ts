import { Media, MediaStatus, MediaType, TextAnalysisResponse } from "@/types";
import { computeStageStatus } from "./status-helpers";

export type PipelineStep = { key: string; label: string; status: string };

/**
 * Estado de cada etapa mostrado na página da mídia.
 *
 * Com o texto pronto, a mídia fica "analisando" até a análise terminar. As
 * etapas da análise seguem o que o backend registrou para cada uma
 * (diagnostics.steps: "ok" ou "failed: ..."). Sem registro: a caminho,
 * enquanto a mídia é analisada; não executada (fator desligado), depois que
 * a análise terminou.
 */
export function mediaPipelineSteps(
  media: Pick<Media, "status" | "media_type">,
  transcriptionStatus: string | null | undefined,
  analysis: Pick<TextAnalysisResponse, "diagnostics"> | null | undefined,
): PipelineStep[] {
  const recorded = (analysis?.diagnostics?.steps ?? {}) as Record<string, string>;
  const analysisStep = (name: string): string => {
    const outcome = recorded[name];
    if (outcome === "ok") return MediaStatus.COMPLETED;
    if (outcome?.startsWith("failed")) return MediaStatus.FAILED;
    if (media.status === MediaStatus.FAILED) return MediaStatus.FAILED;
    if (media.status === MediaStatus.ANALYZING) return MediaStatus.PROCESSING;
    if (media.status === MediaStatus.COMPLETED) return "SKIPPED";
    return MediaStatus.PENDING;
  };
  const isText = media.media_type === MediaType.TEXT;

  return [
    {
      key: "upload",
      label: "Upload e validação",
      status: media.status === MediaStatus.FAILED ? MediaStatus.FAILED : MediaStatus.COMPLETED,
    },
    {
      key: "transcription",
      label: isText ? "Extração do texto" : "Transcrição",
      status: computeStageStatus(media.status, media.media_type, transcriptionStatus),
    },
    { key: "topics", label: "Temas", status: analysisStep("topic_modeling") },
    { key: "sentiment", label: "Tom", status: analysisStep("sentiment") },
    { key: "summary", label: "Resumo", status: analysisStep("synthesis") },
  ];
}
