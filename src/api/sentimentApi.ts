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
