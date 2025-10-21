
import axios from "axios";
import { Transcription } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const transcriptionApi = axios.create({
  baseURL: `${API_URL}/transcriptions`,
});

transcriptionApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const getTranscriptionByMediaId = async (mediaId: string): Promise<Transcription> => {
  const response = await transcriptionApi.get(`/?media_id=${mediaId}`);
  return response.data;
};

export const transcribeAudio = async (
  audioFile: File,
  options?: {
    provider?: string;
    language?: string;
    wordTimestamps?: boolean;
  }
): Promise<any> => {
  const formData = new FormData();
  formData.append("audio_file", audioFile);
  
  if (options?.provider) {
    formData.append("provider", options.provider);
  }
  if (options?.language) {
    formData.append("language", options.language);
  }
  if (options?.wordTimestamps !== undefined) {
    formData.append("word_timestamps", options.wordTimestamps.toString());
  }

  const response = await transcriptionApi.post("/transcribe", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const reprocessTranscription = async (
  mediaId: string,
  options?: {
    provider?: string;
    language?: string;
    force?: boolean;
  }
): Promise<any> => {
  const formData = new FormData();
  formData.append("media_id", mediaId);
  
  if (options?.provider) {
    formData.append("provider", options.provider);
  }
  if (options?.language) {
    formData.append("language", options.language);
  }
  if (options?.force !== undefined) {
    formData.append("force", options.force.toString());
  }

  const response = await transcriptionApi.post("/reprocess", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export default transcriptionApi;
