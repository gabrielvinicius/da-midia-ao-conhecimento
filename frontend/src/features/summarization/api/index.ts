// Chamadas HTTP da análise: leitura, revisão humana e busca semântica.
import api from '@/lib/api';
import { apiErrorStatus } from '@/lib/errors';
import { TextAnalysisResponse } from '@/types';

/** Trecho encontrado pela busca semântica, com o instante na gravação. */
export interface SemanticSearchResult {
  media_id: string;
  content: string;
  relevance: number;
  start?: number | null;
  end?: number | null;
  /** Título do resumo da mídia (o assunto), quando ela já foi analisada. */
  title?: string | null;
  /** Proximidade dada pelo reranqueador; null quando a busca usou só os vetores. */
  match?: "strong" | "related" | "weak" | "unrecognized" | null;
}

/** Análise da mídia, ou null enquanto ela ainda não existe (404). */
export const getAnalysisByMediaId = async (mediaId: string): Promise<TextAnalysisResponse | null> => {
  try {
    return (await api.get<TextAnalysisResponse>(`/text-analysis/media/${mediaId}`)).data;
  } catch (error) {
    if (apiErrorStatus(error) === 404) return null;
    throw error;
  }
};

export const submitAnalysisFeedback = async (analysisId: string, score: number): Promise<void> => {
  await api.post(`/text-analysis/${analysisId}/feedback`, { score });
};

// O texto vai no corpo: resumos longos podem exceder o limite de tamanho da URL.
export const correctSummary = async (analysisId: string, summary: string): Promise<void> => {
  await api.put(`/text-analysis/${analysisId}/summary`, { summary });
};

/** Corrige o título de um tema; o título da IA fica guardado. */
export const renameTopic = async (analysisId: string, topicId: number, title: string): Promise<void> => {
  await api.put(`/text-analysis/${analysisId}/topics/${topicId}`, { title });
};

export interface StudyAidsPayload {
  chapters: { start: number; end: number; title: string }[];
  review_questions: { question: string; answer: string; start: number | null }[];
}

/** Substitui capítulos e perguntas pela versão revisada; a da IA fica guardada. */
export const correctStudyAids = async (analysisId: string, payload: StudyAidsPayload): Promise<void> => {
  await api.put(`/text-analysis/${analysisId}/study`, payload);
};

export const semanticSearch =async (query: string, limit = 10): Promise<SemanticSearchResult[]> =>
  (await api.get<SemanticSearchResult[]>('/text-analysis/search', { params: { query, limit } })).data;

export type ReviewProgress = {
  /** Caixa da revisão espaçada: acertar sobe, errar volta para 1. */
  box: number;
  correct_count: number;
  wrong_count: number;
  last_answered_at: string | null;
  due_at: string | null;
  /** Dominada: chegou à caixa configurada no servidor (REVIEW_MASTERED_BOX). */
  mastered: boolean;
};
export type StudyQuestion = {
  question: string;
  answer: string;
  start: number | null;
  /** null: nunca respondida. */
  progress: ReviewProgress | null;
  /** Para revisar agora. */
  due: boolean;
};
export type StudyDeckEntry = { media_id: string | null; analysis_id: string; questions: StudyQuestion[] };

/** Perguntas de revisão de todas as mídias do usuário, das mais novas para as mais antigas. */
export const getStudyDeck = async (): Promise<StudyDeckEntry[]> =>
  (await api.get<StudyDeckEntry[]>('/text-analysis/study-deck')).data;

/** Registra se o aluno acertou; devolve quando a pergunta volta. */
export const answerReviewQuestion = async (analysisId: string, question: string, correct: boolean): Promise<ReviewProgress> =>
  (await api.post<ReviewProgress>(`/text-analysis/${analysisId}/review-answer`, { question, correct })).data;

export type NotebookEntry = {
  media_id: string | null;
  analysis_id: string;
  summary: string;
  genre: string | null;
  topics: string[];
  chapters: number;
  questions: number;
};

export const getNotebook = async (): Promise<NotebookEntry[]> => (await api.get<NotebookEntry[]>('/text-analysis/notebook')).data;

export type TopicOccurrence = {
  media_id: string | null;
  analysis_id: string;
  title: string;
  keywords: string[];
  snippet: string | null;
  start: number | null;
};
export type TopicGroup = { title: string; media_count: number; occurrences: TopicOccurrence[] };

export const getTopicsOverview = async (): Promise<TopicGroup[]> =>
  (await api.get<TopicGroup[]>('/text-analysis/topics-overview')).data;
