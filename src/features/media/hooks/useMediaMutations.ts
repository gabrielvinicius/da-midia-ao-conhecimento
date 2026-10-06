import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';

import { apiErrorMessage } from '@/lib/errors';
import { removeFromCachedPages, restoreCachedPages } from '@/lib/optimistic';
import { deleteMedia, reprocessMedia, uploadMedia, UploadMediaRequest } from '../api';

export const useUploadMediaMutation = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: (request: UploadMediaRequest) =>
      uploadMedia(request, { onProgress: (percent) => setProgress(percent) }),
    onMutate: () => setProgress(0),
    onSuccess: (data) => {
      toast.success(`Arquivo "${data.filename || 'arquivo'}" enviado. Você será avisado quando o processamento terminar.`);
      setProgress(100);
      queryClient.invalidateQueries({ queryKey: ['media'] });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      navigate('/dashboard');
    },
    onError: (error) => {
      setProgress(0);
      toast.error(apiErrorMessage(error, 'Erro ao fazer upload do arquivo'));
    },
  });

  return { ...mutation, progress };
};

export const useReprocessMediaMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mediaId: string) => reprocessMedia(mediaId),
    onSuccess: (_data, mediaId) => {
      toast.info('Processamento reiniciado. Você será avisado quando terminar.');
      queryClient.invalidateQueries({ queryKey: ['media', mediaId] });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      queryClient.invalidateQueries({ queryKey: ['transcription', mediaId] });
      queryClient.invalidateQueries({ queryKey: ['text-analysis', mediaId] });
      queryClient.invalidateQueries({ queryKey: ['media-stats'] });
    },
    onError: (error) => {
      // 409: a mídia não falhou (já foi reenviada ou está em processamento).
      toast.error(apiErrorMessage(error, 'Não foi possível reprocessar a mídia'));
    },
  });
};

export const useDeleteMediaMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mediaId: string) => deleteMedia(mediaId),
    // Some da lista na hora; volta se a exclusão falhar.
    onMutate: async (mediaId) => {
      await queryClient.cancelQueries({ queryKey: ['media-list'] });
      return { previous: removeFromCachedPages(queryClient, ['media-list'], mediaId) };
    },
    onSuccess: (_data, mediaId) => {
      toast.success('Mídia excluída com sucesso.');
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      queryClient.invalidateQueries({ queryKey: ['media-stats'] });
      queryClient.removeQueries({ queryKey: ['media', mediaId] });
    },
    onError: (error, _mediaId, context) => {
      toast.error(apiErrorMessage(error, 'Erro ao excluir a mídia'));
      restoreCachedPages(queryClient, context?.previous);
    },
  });
};
