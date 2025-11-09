// frontend/src/features/sentiment_analysis/hooks/useSentiment.ts
import { useQuery } from '@tanstack/react-query';
import { useSentimentAnalysisByMediaIdQuery } from '@/hooks/useQueries';

export const useSentimentAnalysis = (mediaId: string) => {
  return useSentimentAnalysisByMediaIdQuery(mediaId);
};
