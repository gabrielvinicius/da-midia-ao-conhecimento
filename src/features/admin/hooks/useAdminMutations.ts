import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import {
  deleteUser,
  deleteMedia,
  updateUser,
  UserUpdatePayload,
  reprocessMedia,
  bulkReprocessFailedMedia,
} from '../api';
import { apiErrorMessage } from '@/lib/errors';
import { removeFromCachedPages, restoreCachedPages } from '@/lib/optimistic';

export const useDeleteUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: () => {
      toast.success('Usuário removido com sucesso.');
      queryClient.invalidateQueries({ queryKey: ['admin-all-users'] });
    },
    onError: (error) => {
      console.error('Failed to delete user:', error);
      toast.error(apiErrorMessage(error, 'Erro ao remover o usuário'));
    },
  });
};

export const useDeleteMedia = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mediaId: string) => deleteMedia(mediaId),
    onMutate: async (mediaId) => {
      await queryClient.cancelQueries({ queryKey: ['admin-all-media'] });
      return { previous: removeFromCachedPages(queryClient, ['admin-all-media'], mediaId) };
    },
    onSuccess: () => {
      toast.success('Mídia excluída com sucesso.');
      queryClient.invalidateQueries({ queryKey: ['admin-all-media'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      queryClient.invalidateQueries({ queryKey: ['media-stats'] });
    },
    onError: (error, _vars, context) => {
      console.error('Failed to delete media:', error);
      restoreCachedPages(queryClient, context?.previous);
      toast.error(apiErrorMessage(error, 'Erro ao excluir mídia'));
    },
  });
};

export const useUpdateUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, payload }: { userId: string; payload: UserUpdatePayload }) => updateUser(userId, payload),
    onSuccess: () => {
      toast.success('Usuário atualizado com sucesso.');
      queryClient.invalidateQueries({ queryKey: ['admin-all-users'] });
    },
    onError: (error) => {
      console.error('Failed to update user:', error);
      toast.error(apiErrorMessage(error, 'Erro ao atualizar o usuário'));
    },
  });
};

export const useReprocessMedia = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mediaId: string) => reprocessMedia(mediaId),
    onSuccess: (data) => {
      toast.success(data.message || 'Reprocessamento iniciado.');
      // Os avisos do processamento (lib/realtime) atualizam a lista depois.
      queryClient.invalidateQueries({ queryKey: ['admin-all-media'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
    },
    onError: (error) => {
      console.error('Failed to reprocess media:', error);
      toast.error(apiErrorMessage(error, 'Erro ao reprocessar a mídia'));
    },
  });
};

export const useBulkReprocessMedia = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => bulkReprocessFailedMedia(),
    onSuccess: (data) => {
      toast.success(data.message || 'Reprocessamento em lote iniciado.');
      queryClient.invalidateQueries({ queryKey: ['admin-all-media'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
    },
    onError: (error) => {
      console.error('Failed to bulk reprocess media:', error);
      toast.error(apiErrorMessage(error, 'Erro ao reprocessar mídia em massa.'));
    },
  });
};
