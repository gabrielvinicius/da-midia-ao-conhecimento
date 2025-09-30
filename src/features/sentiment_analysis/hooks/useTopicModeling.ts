import { useQuery } from '@tanstack/react-query';
import { getAnalysis } from '../api';
import { AnalysisType } from '@/types';

export const useTopicModeling = (mediaId: string) => {
  return useQuery({
    queryKey: ['analysis', mediaId, AnalysisType.TOPIC_MODELING],
    queryFn: () => getAnalysis(mediaId, AnalysisType.TOPIC_MODELING),
    enabled: !!mediaId,
    // Poll for updates if the analysis is not yet available.
    refetchInterval: (query) => {
      if (query.state.data === null) {
        return 5000; // Refetch every 5 seconds until found
      }
      return false; // Stop refetching once data is available
    },
  });
};
