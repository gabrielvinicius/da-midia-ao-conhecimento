import { useQuery } from '@tanstack/react-query';
import { getSummaryByMediaId } from '../api';

// Hook to get summary data for a media item
export const useSummary = (mediaId: string) => {
  return useQuery({
    queryKey: ['summary', mediaId],
    queryFn: () => getSummaryByMediaId(mediaId),
    enabled: !!mediaId, // Only run if mediaId is available
    // Polling is no longer needed, WebSocket provider will push updates.
  });
};
