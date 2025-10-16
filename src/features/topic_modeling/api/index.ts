import api from '@/lib/api';
import { TopicModelingResult } from '@/types';

export const getTopicModeling = async (mediaId: string): Promise<TopicModelingResult> => {
  console.log('🏷️ Buscando topic modeling para mídia:', mediaId);
  
  const response = await api.get<TopicModelingResult>(`/topic-modeling/?media_id=${mediaId}`);
  console.log('✅ Topic modeling obtido:', response.data);
  
  return response.data;
};

export const getAllTopicModeling = async (): Promise<TopicModelingResult[]> => {
  console.log('🏷️ Buscando todos os topic modelings');
  
  const response = await api.get<TopicModelingResult[]>('/topic-modeling/');
  console.log('✅ Topic modelings obtidos:', response.data);
  
  return response.data;
};