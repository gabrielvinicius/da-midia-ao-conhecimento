import api from '@/lib/api';
import { TopicModelingAcceptedResponse, TopicModelingResult } from '@/types';

const handle404 = (error: any) => {
  if (error?.response?.status === 404) {
    return null;
  }
  throw error;
};

export const getTopicModelingResult = async (mediaId: string): Promise<TopicModelingResult | null> => {
  console.log('📊 Buscando resultado de modelagem de tópicos para mídia:', mediaId);
  try {
    const response = await api.get<TopicModelingResult>(`/topic-modeling/?media_id=${mediaId}`);
    console.log('✅ Resultado de modelagem de tópicos obtido:', response.data);
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
  console.log('🔄 Reprocessando modelagem de tópicos para mídia:', mediaId);
  
  const formData = new FormData();
  formData.append('media_id', mediaId);
  
  if (options?.numTopics) {
    formData.append('num_topics', options.numTopics.toString());
  }
  if (options?.force !== undefined) {
    formData.append('force', options.force.toString());
  }

  const response = await api.post<TopicModelingAcceptedResponse>('/topic-modeling/reprocess', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  console.log('✅ Reprocessamento de modelagem de tópicos iniciado:', response.data);
  return response.data;
};

export const getTopicModeling = async (mediaId: string): Promise<TopicModelingResult | null> => {
  console.log('🏷️ Buscando topic modeling para mídia:', mediaId);
  try {
    const response = await api.get<TopicModelingResult>(`/topic-modeling/?media_id=${mediaId}`);
    console.log('✅ Topic modeling obtido:', response.data);
    return response.data;
  } catch (error: any) {
    return handle404(error);
  }
};

export const getAllTopicModeling = async (): Promise<TopicModelingResult[]> => {
  console.log('🏷️ Buscando todos os topic modelings');
  
  const response = await api.get<TopicModelingResult[]>('/topic-modeling/');
  console.log('✅ Topic modelings obtidos:', response.data);
  
  return response.data;
};
