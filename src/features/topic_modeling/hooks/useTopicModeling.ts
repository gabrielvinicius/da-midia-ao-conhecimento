import { useQuery } from '@tanstack/react-query';
import { getTopicModeling } from '../api';

export const useTopicModeling = (mediaId: string) => {
  return useQuery({
    queryKey: ['topic-modeling', mediaId],
    queryFn: () => getTopicModeling(mediaId),
    enabled: !!mediaId,
    refetchOnWindowFocus: false,
    staleTime: 30_000,
  });
};
