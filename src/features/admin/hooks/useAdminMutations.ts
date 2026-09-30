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
    },
  });
};

export const useDeleteMedia = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mediaId: string) => deleteMedia(mediaId),
    onMutate: async (mediaId) => {
      await queryClient.cancelQueries({ queryKey: ['admin-all-media'] });
      const previous = queryClient.getQueryData<any>(['admin-all-media']);
      if (previous && Array.isArray(previous.items)) {
        const items = previous.items.filter((m: any) => m.id !== mediaId);
        const total = typeof previous.total === 'number' ? Math.max(0, previous.total - 1) : items.length;
        queryClient.setQueryData(['admin-all-media'], { ...previous, items, total });
      }
      return { previous };
    },
    onSuccess: () => {
      toast.success('Mídia excluída com sucesso.');
      queryClient.invalidateQueries({ queryKey: ['admin-all-media'] });
      queryClient.invalidateQueries({ queryKey: ['media-stats'] });
    },
    onError: (error, _vars, context) => {
      console.error('Failed to delete media:', error);
      if (context?.previous) {
        queryClient.setQueryData(['admin-all-media'], context.previous);
      }
      toast.error('Erro ao excluir mídia');
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
    },
  });
};

export const useReprocessMedia = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mediaId: string) => reprocessMedia(mediaId),
    onSuccess: (data) => {
      toast.success(data.message || 'Reprocessamento iniciado.');
      // No need to invalidate queries here. The WebSocket update will refresh the UI.
      // We can, however, invalidate to get the initial PENDING state faster if needed.
      queryClient.invalidateQueries({ queryKey: ['admin-all-media'] });
    },
    onError: (error) => {
      console.error('Failed to reprocess media:', error);
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
    },
    onError: (error) => {
      console.error('Failed to bulk reprocess media:', error);
      toast.error('Erro ao reprocessar mídia em massa.');
    },
  });
};
