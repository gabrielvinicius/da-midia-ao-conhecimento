// Arquivos para baixar, montados no navegador a partir do que a página já tem.
import { formatClock, srtTime, vttTime } from "@/lib/time";
import type { Media, TextAnalysisResponse, Transcription } from "@/types";
import {
  chaptersOf,
  questionsOf,
  screenMomentsOf,
  splitSummary,
  summaryTitle,
  toneCounts,
  topicsInOrder,
} from "./analysisContent";

export type ExportInput = {
  media: Media;
  analysis?: TextAnalysisResponse | null;
  transcription?: Transcription | null;
};

/** Nome de arquivo a partir do nome da mídia, sem extensão nem caracteres problemáticos. */
export const baseFileName = (media: Media): string => {
  const name = (media.filename || media.id).replace(/\.[^.]+$/, "");
  const cleaned = name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^\w.-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
  return cleaned || "midia";
};

const stamp = (seconds: number | null | undefined) => (seconds == null ? "" : `[${formatClock(seconds)}] `);

/** Só o resumo (sem o apêndice), em Markdown. */
export const summaryMarkdown = ({ analysis }: ExportInput): string => splitSummary(analysis?.summary).body + "\n";

/**
 * Guia de estudo completo em Markdown: resumo, capítulos, perguntas com
 * respostas, temas, tom e o que aparecia na tela.
 */
export const studyGuideMarkdown = (input: ExportInput): string => {
  const { media, analysis, transcription } = input;
  const out: string[] = [];
  const body = splitSummary(analysis?.summary).body;
  const title = summaryTitle(analysis?.summary);
  if (!title) out.push(`# ${media.filename || "Mídia"}`, "");
  out.push(body || "_Sem resumo._", "");
  out.push("---", "", `Arquivo: ${media.filename || media.id}`);
  const duration = transcription?.duration ?? media.duration;
  if (duration) out.push(`Duração: ${formatClock(duration)}`);
  out.push("");

  const chapters = chaptersOf(analysis);
  if (chapters.length) {
    out.push("## Capítulos", "", ...chapters.map((c) => `- ${stamp(c.start)}${c.title}`), "");
  }
  const questions = questionsOf(analysis);
  if (questions.length) {
    out.push("## Perguntas de revisão", "");
    questions.forEach((q, i) => {
      out.push(`${i + 1}. ${q.question}`, `   - Resposta: ${q.answer}${q.start != null ? ` (${formatClock(q.start)})` : ""}`);
    });
    out.push("");
  }
  const topics = topicsInOrder(analysis);
  if (topics.length) {
    out.push("## Temas", "");
    topics.forEach((t) => {
      const keywords = t.keywords?.length ? ` — ${t.keywords.slice(0, 6).join(", ")}` : "";
      out.push(`- ${stamp(t.start)}**${t.title || "Tema"}**${keywords}`);
    });
    out.push("");
  }
  const tone = toneCounts(analysis);
  if (tone.total) {
    out.push(
      "## Tom",
      "",
      `${tone.negative} trechos negativos, ${tone.neutral} neutros e ${tone.positive} positivos (de ${tone.total}).`,
      "",
    );
  }
  const screen = screenMomentsOf(analysis);
  if (screen.length) {
    out.push("## O que aparecia na tela", "", ...screen.map((s) => `- ${stamp(s.start)}${s.text}`), "");
  }
  return out.join("\n");
};

const segmentsOf = (transcription?: Transcription | null) =>
  (transcription?.segments ?? []).filter((s) => s.text.trim());

/** Transcrição em texto: com horários quando houver trechos com tempo. */
export const transcriptText = ({ transcription }: ExportInput): string => {
  const segments = segmentsOf(transcription);
  if (!segments.length) return (transcription?.text ?? "").trim() + "\n";
  return segments.map((s) => `${stamp(s.start)}${s.text.trim()}`).join("\n") + "\n";
};

export const transcriptSrt = ({ transcription }: ExportInput): string =>
  segmentsOf(transcription)
    .map((s, i) => `${i + 1}\n${srtTime(s.start)} --> ${srtTime(s.end)}\n${s.text.trim()}\n`)
    .join("\n");

export const transcriptVtt = ({ transcription }: ExportInput): string =>
  "WEBVTT\n\n" +
  segmentsOf(transcription)
    .map((s) => `${vttTime(s.start)} --> ${vttTime(s.end)}\n${s.text.trim()}\n`)
    .join("\n");

/** Tudo o que foi extraído, em JSON, para reaproveitar em outras ferramentas. */
export const everythingJson = ({ media, analysis, transcription }: ExportInput): string => {
  const { body } = splitSummary(analysis?.summary);
  return JSON.stringify(
    {
      media: {
        id: media.id,
        filename: media.filename,
        media_type: media.media_type,
        created_at: media.created_at,
        duration: transcription?.duration ?? media.duration ?? null,
      },
      summary: body || null,
      genre: analysis?.diagnostics?.genre ?? null,
      chapters: chaptersOf(analysis),
      review_questions: questionsOf(analysis),
      topics: topicsInOrder(analysis).map((t) => ({
        title: t.title,
        start: t.start ?? null,
        keywords: t.keywords,
        snippets: t.representative_snippets,
      })),
      tone: toneCounts(analysis),
      screen: screenMomentsOf(analysis),
      grounding: analysis?.diagnostics?.grounding ?? null,
      transcript: {
        language: transcription?.language ?? null,
        text: transcription?.text ?? "",
        segments: (transcription?.segments ?? []).map((s) => ({ start: s.start, end: s.end, text: s.text })),
      },
    },
    null,
    2,
  );
};
