import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { deleteUser, deleteMedia, updateUser, UserUpdatePayload, reprocessMedia } from '../api';

export const useDeleteUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: () => {
      toast.success('User deleted successfully.');
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
    onSuccess: () => {
      toast.success('Media deleted successfully.');
      queryClient.invalidateQueries({ queryKey: ['admin-all-media'] });
    },
    onError: (error) => {
      console.error('Failed to delete media:', error);
    },
  });
};

export const useUpdateUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, payload }: { userId: string; payload: UserUpdatePayload }) => updateUser(userId, payload),
    onSuccess: () => {
      toast.success('User updated successfully.');
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
      toast.success(data.message || 'Reprocessing initiated.');
      // No need to invalidate queries here. The WebSocket update will refresh the UI.
      // We can, however, invalidate to get the initial PENDING state faster if needed.
      queryClient.invalidateQueries({ queryKey: ['admin-all-media'] });
    },
    onError: (error) => {
      console.error('Failed to reprocess media:', error);
    },
  });
};
