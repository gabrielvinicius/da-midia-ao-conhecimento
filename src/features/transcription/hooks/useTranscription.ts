import { useQuery } from '@tanstack/react-query';
import { getTranscriptionByMediaId } from '../api';
import { TranscriptionStatus } from '../../../types';

// Hook to get transcription data for a media item
export const useTranscription = (mediaId: string) => {
  return useQuery({
    queryKey: ['transcription', mediaId],
    queryFn: () => getTranscriptionByMediaId(mediaId),
    enabled: !!mediaId, // Only run if mediaId is available
    // Poll for updates if the transcription is still processing
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === TranscriptionStatus.PROCESSING || data?.status === TranscriptionStatus.PENDING) {
        return 5000; // Refetch every 5 seconds
      }
      return false; // Stop refetching if completed or failed
    },
  });
};
