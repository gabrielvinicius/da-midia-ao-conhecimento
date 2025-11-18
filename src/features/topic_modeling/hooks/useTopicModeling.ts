import { useQuery } from '@tanstack/react-query';
import { getTopicModeling } from '../api';

export const useTopicModeling = (mediaId: string) => {
  return useQuery({
    queryKey: ['topic-modeling', mediaId],
    queryFn: () => getTopicModeling(mediaId),
    enabled: !!mediaId,
    refetchInterval: (query) => (!query.state.data ? 10000 : false),
  });
};
