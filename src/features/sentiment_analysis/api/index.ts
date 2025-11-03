import api from "@/lib/api";
import { SentimentAnalysisAcceptedResponse, SentimentAnalysisResult } from "@/types";

export const getSentimentAnalysis = async (mediaId: string): Promise<SentimentAnalysisResult> => {
  console.log('🎭 Buscando análise de sentimento para mídia:', mediaId);
  
  const response = await api.get<SentimentAnalysisResult>(`/sentiment-analysis/?media_id=${mediaId}`);
  console.log('✅ Análise de sentimento obtida:', response.data);
  
  return response.data;
};

export const getAllSentimentAnalyses = async (): Promise<SentimentAnalysisResult[]> => {
  console.log('🎭 Buscando todas as análises de sentimento');
  
  const response = await api.get<SentimentAnalysisResult[]>('/sentiment-analysis/');
  console.log('✅ Análises de sentimento obtidas:', response.data);
  
  return response.data;
};

export const reprocessSentimentAnalysis = async (
  mediaId: string,
  options?: {
    provider?: string;
    force?: boolean;
  }
): Promise<SentimentAnalysisAcceptedResponse> => {
  console.log('🔄 Reprocessando análise de sentimento para mídia:', mediaId);
  
  const formData = new FormData();
  formData.append('media_id', mediaId);
  
  if (options?.provider) {
    formData.append('provider', options.provider);
  }
  if (options?.force !== undefined) {
    formData.append('force', options.force.toString());
  }

  const response = await api.post<SentimentAnalysisAcceptedResponse>('/sentiment-analysis/reprocess', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  console.log('✅ Reprocessamento de análise de sentimento iniciado:', response.data);
  return response.data;
};

// Legacy function for compatibility
export const getAnalysis = async (mediaId: string, type: string): Promise<SentimentAnalysisResult | null> => {
  try {
    if (type === 'SENTIMENT') {
      return await getSentimentAnalysis(mediaId);
    }
    return null;
  } catch (error: any) {
    if (error.response && error.response.status === 404) {
      return null;
    }
    throw error;
  }
};
