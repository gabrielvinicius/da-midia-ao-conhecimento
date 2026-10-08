// Dados de exemplo no formato da API (parecidos com os de uma aula real) e
// um render com o React Query, para os componentes que corrigem dados.
import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { MediaStatus, MediaType, TranscriptionStatus, type Media, type TextAnalysisResponse, type Transcription } from "@/types";

export const renderWithQuery = (ui: ReactElement) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return { client, ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>) };
};

export const SUMMARY_BODY = [
  "# A crise da engenharia de software",
  "",
  "O apresentador argumenta que a profissão vive uma **crise**.",
  "",
  "## Pontos-chave",
  "- Dijkstra publicou sobre programação estruturada em 1970.",
  "- O manifesto ágil teve 17 autores.",
].join("\n");

export const SUMMARY_APPENDIX =
  "\n\n---\n# Apêndice: trechos por tema\n### A crise\n> [00:00] Estamos diante de uma crise.\n>\n> [00:30] Outro trecho.";

export const media = (overrides: Partial<Media> = {}): Media => ({
  id: "m1",
  user_id: "u1",
  filename: "a-história-não-contada.mp4",
  content_type: "video/mp4",
  size: 1000,
  media_type: MediaType.VIDEO,
  status: MediaStatus.COMPLETED,
  created_at: "2026-10-07T16:43:00Z",
  ...overrides,
});

export const analysis = (overrides: Partial<TextAnalysisResponse> = {}): TextAnalysisResponse => ({
  analysis_id: "a1",
  document_id: "d1",
  media_id: "m1",
  overall_sentiment: "negative",
  summary: SUMMARY_BODY + SUMMARY_APPENDIX,
  sentiment_items: [
    { chunk_id: "1", label: "negative", score: 0.8, text: "Crise.", start: 0, end: 60 },
    { chunk_id: "2", label: "neutral", score: 0.7, text: "Exemplo.", start: 60, end: 120 },
    { chunk_id: "3", label: "negative", score: 0.6, text: "Alerta.", start: 120, end: 180 },
    { chunk_id: "4", label: "positive", score: 0.9, text: "Esperança.", start: 180, end: 240 },
  ],
  topics: [
    { topic_id: 1, title: "A era da IA", keywords: ["ia", "código"], representative_snippets: ["A IA aprendeu."], size: 3, start: 1310 },
    { topic_id: 0, title: "A origem do caos", keywords: ["década", "crise"], representative_snippets: ["Nos anos 60."], size: 1, start: 0 },
    { topic_id: -1, title: "ruído", keywords: [], representative_snippets: [], size: 9 },
  ],
  diagnostics: {
    genre: "opiniao",
    steps: { topic_modeling: "ok" },
    chapters: [
      { start: 0, end: 600, title: "A crise do software" },
      { start: 600, end: 1310, title: "O manifesto ágil" },
      { start: 1310, end: 1780, title: "A era da IA generativa" },
    ],
    review_questions: [
      { question: "Quantos autores teve o manifesto ágil?", answer: "17 desenvolvedores.", start: 740 },
      { question: "O que é vibe coding?", answer: "Programar sem entender.", start: null },
    ],
    visual_context: ["[05:32] Um slide com o texto \"Clean Code\".", "sem horário"],
    grounding: { checked: 3, supported: 3, ratio: 1, threshold: 0.8, unsupported: [], gaps: [], number_issues: [] },
  },
  ...overrides,
});

export const transcription = (overrides: Partial<Transcription> = {}): Transcription => ({
  id: "t1",
  media_id: "m1",
  status: TranscriptionStatus.COMPLETED,
  provider: "default",
  created_at: "2026-10-07T16:43:00Z",
  processed_at: "2026-10-07T16:45:00Z",
  error_message: null,
  text: "Estamos diante de uma crise. Vamos falar de clin code.",
  segments: [
    { start: 0, end: 3.5, text: " Estamos diante de uma crise." },
    { start: 3.5, end: 7.25, text: " Vamos falar de clin code." },
  ],
  speaker_aliases: {},
  language: "pt",
  duration: 1780,
  corrected_segments: 0,
  ...overrides,
});
