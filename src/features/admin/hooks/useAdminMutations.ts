import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import { deleteUser, deleteMedia } from '../api';

export const useDeleteUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: () => {
      toast.success('User deleted successfully.');
      // Invalidate the users query to refetch the list
      queryClient.invalidateQueries({ queryKey: ['admin-all-users'] });
    },
    onError: (error) => {
      // The global error handler in `lib/api.ts` will already show a toast
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
      // Invalidate the media query to refetch the list
      queryClient.invalidateQueries({ queryKey: ['admin-all-media'] });
    },
    onError: (error) => {
      console.error('Failed to delete media:', error);
    },
  });
};
