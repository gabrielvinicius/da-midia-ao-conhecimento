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

export const semanticSearch = async (query: string, limit = 10): Promise<SemanticSearchResult[]> =>
  (await api.get<SemanticSearchResult[]>('/text-analysis/search', { params: { query, limit } })).data;
