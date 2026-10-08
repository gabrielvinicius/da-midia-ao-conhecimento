import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { correctTranscriptionSegment, updateSpeakerAliases } from '../api';
import { apiErrorMessage } from '@/lib/errors';

export const useUpdateSpeakerAliases = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ transcriptionId, aliases }: { transcriptionId: string; aliases: Record<string, string> }) =>
      updateSpeakerAliases(transcriptionId, aliases),
    onSuccess: (data) => {
      toast.success('Nomes dos falantes atualizados.');
      // Manually update the cache with the new data to avoid a refetch
      queryClient.setQueryData(['transcription', data.media_id], data);
    },
    onError: (error) => {
      toast.error(apiErrorMessage(error, 'Não foi possível salvar os nomes dos falantes.'));
    },
  });
};

/** Correção de um trecho da transcrição; a resposta substitui a transcrição no cache. */
export const useCorrectSegment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ transcriptionId, index, text }: { transcriptionId: string; index: number; text: string }) =>
      correctTranscriptionSegment(transcriptionId, index, text),
    onSuccess: (data) => {
      toast.success('Trecho corrigido.');
      queryClient.setQueryData(['transcription', data.media_id], data);
    },
    onError: (error) => {
      toast.error(apiErrorMessage(error, 'Não foi possível salvar a correção do trecho.'));
    },
  });
};
