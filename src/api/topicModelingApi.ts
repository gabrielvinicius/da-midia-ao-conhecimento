// frontend/src/api/topicModelingApi.ts
import axios from "axios";
import { TopicModelingResult } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const topicModelingApi = axios.create({
  baseURL: `${API_URL}/topic-modeling`,
});

topicModelingApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const getTopicModelingResultByMediaId = async (mediaId: string): Promise<TopicModelingResult> => {
  const response = await topicModelingApi.get(`/?media_id=${mediaId}`);
  return response.data;
};
