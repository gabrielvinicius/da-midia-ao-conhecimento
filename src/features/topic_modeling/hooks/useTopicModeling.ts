// frontend/src/features/topic_modeling/hooks/useTopicModeling.ts
import { useQuery } from '@tanstack/react-query';
import { getTopicModelingResultByMediaId } from '../../../api/topicModelingApi';

export const useTopicModeling = (mediaId: string) => {
  return useQuery({
    queryKey: ['topicModeling', mediaId],
    queryFn: () => getTopicModelingResultByMediaId(mediaId),
    enabled: !!mediaId, // Only run the query if the mediaId is available
    retry: 1, // Don't retry endlessly if the analysis isn't ready yet
  });
};
