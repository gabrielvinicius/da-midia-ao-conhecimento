// frontend/src/api/sentimentApi.ts
import axios from "axios";
import { SentimentAnalysisResult } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const sentimentApi = axios.create({
  baseURL: `${API_URL}/sentiment-analysis`,
});

sentimentApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const getSentimentAnalysisByMediaId = async (mediaId: string): Promise<SentimentAnalysisResult> => {
  const response = await sentimentApi.get(`/?media_id=${mediaId}`);
  return response.data;
};

export const reprocessSentimentAnalysis = async (
  mediaId: string,
  options?: {
    provider?: string;
    force?: boolean;
  }
): Promise<any> => {
  const formData = new FormData();
  formData.append("media_id", mediaId);
  
  if (options?.provider) {
    formData.append("provider", options.provider);
  }
  if (options?.force !== undefined) {
    formData.append("force", options.force.toString());
  }

  const response = await sentimentApi.post("/reprocess", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export default sentimentApi;
