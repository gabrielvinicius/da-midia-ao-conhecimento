import { useQuery } from '@tanstack/react-query';
import { getAnalysis } from '../api';
import { AnalysisType } from '@/types';

export const useSentimentAnalysis = (mediaId: string) => {
  return useQuery({
    queryKey: ['analysis', mediaId, AnalysisType.SENTIMENT],
    queryFn: () => getAnalysis(mediaId, AnalysisType.SENTIMENT),
    enabled: !!mediaId,
    // Poll for updates if the analysis is not yet available.
    // A 404 from the API will be treated as `data: null` and will trigger a refetch.
    refetchInterval: (query) => {
      if (query.state.data === null) {
        return 5000; // Refetch every 5 seconds until found
      }
      return false; // Stop refetching once data is available
    },
  });
};
