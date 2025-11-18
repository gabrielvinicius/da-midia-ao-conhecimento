// frontend/src/api/sentimentApi.ts
import api from "@/lib/api";
import { SentimentAnalysisResult, SentimentAnalysisAcceptedResponse } from "../types";

const handle404 = (error: any) => {
  if (error?.response?.status === 404) {
    return null;
  }
  throw error;
};

export const getSentimentAnalysisByMediaId = async (mediaId: string): Promise<SentimentAnalysisResult | null> => {
  try {
    const response = await api.get(`/sentiment-analysis/?media_id=${mediaId}`);
    return response.data;
  } catch (error: any) {
    return handle404(error);
  }
};

export const reprocessSentimentAnalysis = async (
  transcriptionId: string,
  options?: {
    provider?: string;
    force?: boolean;
  }
): Promise<SentimentAnalysisAcceptedResponse> => {
  const formData = new FormData();
  formData.append("transcription_id", transcriptionId);
  
  if (options?.provider) {
    formData.append("provider", options.provider);
  }
  if (options?.force !== undefined) {
    formData.append("force", options.force.toString());
  }

  const response = await api.post<SentimentAnalysisAcceptedResponse>("/sentiment-analysis/reprocess", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export default { getSentimentAnalysisByMediaId, reprocessSentimentAnalysis };
