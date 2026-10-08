// Leitura do que a análise produziu, no formato que a página e as exportações usam.
import { parseClock } from "@/lib/time";
import type { TextAnalysisResponse } from "@/types";

export type Chapter = { start: number; end: number; title: string };
export type ReviewQuestion = { question: string; answer: string; start: number | null };
export type ScreenMoment = { start: number | null; text: string };

/**
 * O backend grava o resumo seguido de um apêndice (trechos por tema e o que
 * aparecia na tela) depois deste marcador. A página mostra esses dados em
 * abas próprias; o resumo corrigido é gravado de volta com o apêndice.
 */
export const APPENDIX_MARKER = "\n\n---\n# Apêndice";

export const splitSummary = (summary?: string | null): { body: string; appendix: string } => {
  const text = summary ?? "";
  const at = text.indexOf(APPENDIX_MARKER);
  return at < 0 ? { body: text.trim(), appendix: "" } : { body: text.slice(0, at).trim(), appendix: text.slice(at) };
};

/** Primeiro título "# ..." do resumo: o assunto da mídia, mais claro que o nome do arquivo. */
export const summaryTitle = (summary?: string | null): string | null => {
  const line = splitSummary(summary).body.split("\n").find((l) => /^#\s+\S/.test(l.trim()));
  return line ? line.trim().replace(/^#\s+/, "") : null;
};

const diagnostics = (analysis?: TextAnalysisResponse | null) => (analysis?.diagnostics ?? {}) as Record<string, unknown>;

export const chaptersOf = (analysis?: TextAnalysisResponse | null): Chapter[] =>
  (diagnostics(analysis).chapters as Chapter[] | undefined) ?? [];

export const questionsOf = (analysis?: TextAnalysisResponse | null): ReviewQuestion[] =>
  (diagnostics(analysis).review_questions as ReviewQuestion[] | undefined) ?? [];

/** "[05:32] Um quadro com..." → { start: 332, text: "Um quadro com..." }. */
export const screenMomentsOf = (analysis?: TextAnalysisResponse | null): ScreenMoment[] =>
  ((diagnostics(analysis).visual_context as string[] | undefined) ?? []).map((line) => {
    const match = /^\[([\d:]+)\]\s*(.*)$/s.exec(line.trim());
    return match ? { start: parseClock(match[1]), text: match[2] } : { start: null, text: line };
  });

/** Temas reais (sem o grupo de ruído, -1), na ordem em que aparecem na gravação. */
export const topicsInOrder = (analysis?: TextAnalysisResponse | null) =>
  [...(analysis?.topics ?? [])]
    .filter((t) => t.topic_id !== -1)
    .sort((a, b) => (a.start ?? Number.MAX_VALUE) - (b.start ?? Number.MAX_VALUE));

export type ToneCounts = { positive: number; neutral: number; negative: number; total: number };

export const toneCounts = (analysis?: TextAnalysisResponse | null): ToneCounts => {
  const counts = { positive: 0, neutral: 0, negative: 0, total: 0 };
  for (const item of analysis?.sentiment_items ?? []) {
    const label = String(item.label).toLowerCase();
    if (label === "positive" || label === "neutral" || label === "negative") {
      counts[label] += 1;
      counts.total += 1;
    }
  }
  return counts;
};

/** Capítulo em que o reprodutor está (o último que já começou). */
export const activeChapterIndex = (chapters: Chapter[], time: number): number => {
  let active = -1;
  chapters.forEach((chapter, index) => {
    if (time >= chapter.start) active = index;
  });
  return active;
};
