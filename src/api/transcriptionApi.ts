
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

export default transcriptionApi;
