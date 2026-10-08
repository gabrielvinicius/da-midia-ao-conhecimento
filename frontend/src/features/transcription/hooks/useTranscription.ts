import { useQuery } from '@tanstack/react-query';
import { getTranscriptionByMediaId } from '../api';

// Hook to get transcription data for a media item
export const useTranscription = (mediaId: string) => {
  return useQuery({
    queryKey: ['transcription', mediaId],
    queryFn: () => getTranscriptionByMediaId(mediaId),
    enabled: !!mediaId, // Only run if mediaId is available
    // Polling is no longer needed, WebSocket provider will push updates.
  });
};
