// frontend/src/api/topicModelingApi.ts
import axios from "axios";
import { TopicModelingAcceptedResponse, TopicModelingResult } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const topicModelingApi = axios.create({
  baseURL: `${API_URL}/topic-modeling`,
  withCredentials: true,
});

const handle404 = (error: any) => {
  if (error?.response?.status === 404) {
    return null;
  }
  throw error;
};

export const getTopicModelingResultByMediaId = async (mediaId: string): Promise<TopicModelingResult | null> => {
  try {
    const response = await topicModelingApi.get(`/?media_id=${mediaId}`);
    return response.data;
  } catch (error: any) {
    return handle404(error);
  }
};

export const reprocessTopicModeling = async (
  mediaId: string,
  options?: {
    numTopics?: number;
    force?: boolean;
  }
): Promise<TopicModelingAcceptedResponse> => {
  const formData = new FormData();
  formData.append("media_id", mediaId);
  
  if (options?.numTopics) {
    formData.append("num_topics", options.numTopics.toString());
  }
  if (options?.force !== undefined) {
    formData.append("force", options.force.toString());
  }

  const response = await topicModelingApi.post<TopicModelingAcceptedResponse>("/reprocess", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export default topicModelingApi;
