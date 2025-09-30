// frontend/src/features/sentiment_analysis/hooks/useSentiment.ts
import { useQuery } from '@tanstack/react-query';
import { getSentimentAnalysisByMediaId } from '../../../api/sentimentApi';

export const useSentimentAnalysis = (mediaId: string) => {
  return useQuery({
    queryKey: ['sentimentAnalysis', mediaId],
    queryFn: () => getSentimentAnalysisByMediaId(mediaId),
    enabled: !!mediaId, // Only run the query if the mediaId is available
    retry: 1, // Don't retry endlessly if the analysis isn't ready yet
  });
};
