// frontend/src/api/sentimentApi.ts
import axios from "axios";
import { SentimentAnalysisResult, SentimentAnalysisAcceptedResponse } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const sentimentApi = axios.create({
  baseURL: `${API_URL}/sentiment-analysis`,
  withCredentials: true,
});

const handle404 = (error: any) => {
  if (error?.response?.status === 404) {
    return null;
  }
  throw error;
};

export const getSentimentAnalysisByMediaId = async (mediaId: string): Promise<SentimentAnalysisResult | null> => {
  try {
    const response = await sentimentApi.get(`/?media_id=${mediaId}`);
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

  const response = await sentimentApi.post<SentimentAnalysisAcceptedResponse>("/reprocess", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export default sentimentApi;
