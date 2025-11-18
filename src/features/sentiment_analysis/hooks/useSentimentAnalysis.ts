import { useQuery } from '@tanstack/react-query';
import { getSentimentAnalysis } from '../api';

export const useSentimentAnalysis = (mediaId: string) => {
  return useQuery({
    queryKey: ['sentiment-analysis', mediaId],
    queryFn: () => getSentimentAnalysis(mediaId),
    enabled: !!mediaId,
    refetchInterval: (query) => (!query.state.data ? 10000 : false),
  });
};
