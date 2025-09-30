import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { updateSpeakerAliases } from '../api';

export const useUpdateSpeakerAliases = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ transcriptionId, aliases }: { transcriptionId: string; aliases: Record<string, string> }) => 
      updateSpeakerAliases(transcriptionId, aliases),
    onSuccess: (data) => {
      toast.success('Speaker names updated successfully.');
      // Manually update the cache with the new data to avoid a refetch
      queryClient.setQueryData(['transcription', data.media_id], data);
    },
    onError: (error) => {
      console.error('Failed to update speaker names:', error);
    },
  });
};
