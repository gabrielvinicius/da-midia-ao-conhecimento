import { describe, expect, it } from "vitest";
import { MediaStatus, MediaType, TranscriptionStatus } from "@/types";
import { mediaPipelineSteps } from "./pipelineSteps";

const statusOf = (steps: ReturnType<typeof mediaPipelineSteps>) =>
  Object.fromEntries(steps.map((s) => [s.key, s.status]));

describe("mediaPipelineSteps", () => {
  it("com o texto pronto e a análise rodando, as etapas da análise não aparecem concluídas", () => {
    const steps = statusOf(
      mediaPipelineSteps({ status: MediaStatus.ANALYZING, media_type: MediaType.VIDEO }, TranscriptionStatus.COMPLETED, null),
    );
    expect(steps).toMatchObject({ upload: MediaStatus.COMPLETED, transcription: TranscriptionStatus.COMPLETED, topics: MediaStatus.PROCESSING, summary: MediaStatus.PROCESSING });
  });

  it("segue o resultado de cada etapa registrado pela análise", () => {
    const analysis = { diagnostics: { steps: { topic_modeling: "ok", sentiment: "failed: sem GPU" } } };
    const steps = statusOf(
      mediaPipelineSteps({ status: MediaStatus.ANALYZING, media_type: MediaType.AUDIO }, TranscriptionStatus.COMPLETED, analysis),
    );
    expect(steps).toMatchObject({ topics: MediaStatus.COMPLETED, sentiment: MediaStatus.FAILED, summary: MediaStatus.PROCESSING });
  });

  it("com a análise concluída, etapa sem registro foi desligada, não está a caminho", () => {
    const analysis = { diagnostics: { steps: { synthesis: "ok" } } };
    const steps = statusOf(
      mediaPipelineSteps({ status: MediaStatus.COMPLETED, media_type: MediaType.AUDIO }, TranscriptionStatus.COMPLETED, analysis),
    );
    expect(steps).toMatchObject({ summary: MediaStatus.COMPLETED, sentiment: "SKIPPED" });
  });

  it("mídia que falhou mostra a falha", () => {
    const steps = statusOf(
      mediaPipelineSteps({ status: MediaStatus.FAILED, media_type: MediaType.TEXT }, TranscriptionStatus.FAILED, null),
    );
    expect(steps).toMatchObject({ upload: MediaStatus.FAILED, transcription: TranscriptionStatus.FAILED, summary: MediaStatus.FAILED });
  });

  it("documento chama a etapa de extração do texto", () => {
    const [, transcription] = mediaPipelineSteps({ status: MediaStatus.PROCESSING, media_type: MediaType.TEXT }, undefined, null);
    expect(transcription.label).toBe("Extração do texto");
  });
});
