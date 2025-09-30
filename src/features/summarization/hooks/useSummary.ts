import { useQuery } from '@tanstack/react-query';
import { getSummaryByMediaId } from '../api';
import { SummaryStatus } from '../../../types';

// Hook to get summary data for a media item
export const useSummary = (mediaId: string) => {
  return useQuery({
    queryKey: ['summary', mediaId],
    queryFn: () => getSummaryByMediaId(mediaId),
    enabled: !!mediaId, // Only run if mediaId is available
    // Poll for updates if the summary is still processing
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === SummaryStatus.PROCESSING || data?.status === SummaryStatus.PENDING) {
        return 5000; // Refetch every 5 seconds
      }
      return false; // Stop refetching if completed or failed
    },
  });
};
