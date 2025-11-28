import { useQuery } from '@tanstack/react-query';
import { getAnalysis } from '../api';
import { AnalysisType } from '@/types';

export const useTopicModeling = (mediaId: string) => {
  return useQuery({
    queryKey: ['analysis', mediaId, AnalysisType.TOPIC_MODELING],
    queryFn: () => getAnalysis(mediaId, AnalysisType.TOPIC_MODELING),
    enabled: !!mediaId,
    refetchOnWindowFocus: false,
    staleTime: 30_000,
  });
};
