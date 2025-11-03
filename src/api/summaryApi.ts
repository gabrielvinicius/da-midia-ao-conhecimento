
import axios from "axios";
import { Summary, SummarizationReprocessResponse } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const summaryApi = axios.create({
  baseURL: `${API_URL}/summaries`,
});

summaryApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const getSummaryByMediaId = async (mediaId: string): Promise<Summary> => {
  const response = await summaryApi.get(`/?media_id=${mediaId}`);
  return response.data;
};

export const reprocessSummarization = async (
  mediaId: string,
  options?: {
    provider?: string;
    maxLength?: number;
    force?: boolean;
  }
): Promise<SummarizationReprocessResponse> => {
  const formData = new FormData();
  formData.append("media_id", mediaId);
  
  if (options?.provider) {
    formData.append("provider", options.provider);
  }
  if (options?.maxLength) {
    formData.append("max_length", options.maxLength.toString());
  }
  if (options?.force !== undefined) {
    formData.append("force", options.force.toString());
  }

  const response = await summaryApi.post<SummarizationReprocessResponse>("/reprocess", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export default summaryApi;
