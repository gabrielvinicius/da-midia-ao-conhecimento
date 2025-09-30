import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { listMedia, getMediaById, uploadMedia } from '../api';

// Hook to get the list of all media items
export const useMediaList = () => {
  return useQuery({
    queryKey: ['mediaList'],
    queryFn: listMedia,
  });
};

// Hook to get details of a single media item
export const useMediaDetail = (id: string) => {
  return useQuery({
    queryKey: ['mediaDetail', id],
    queryFn: () => getMediaById(id),
    enabled: !!id, // Only run the query if the id is available
  });
};

// Hook for the media upload mutation
export const useUploadMedia = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, storageProvider }: { file: File; storageProvider: string }) => 
      uploadMedia(file, storageProvider),
    onSuccess: (data) => {
      toast.success(`Media "${data.original_file_path}" uploaded successfully! Processing has started.`);
      // Invalidate the media list to refetch and show the new item
      queryClient.invalidateQueries({ queryKey: ['mediaList'] });
      // Navigate to the dashboard to see the new media
      navigate('/dashboard');
    },
    onError: (error) => {
      // The global error handler in `lib/api.ts` will show a toast
      console.error('Upload failed:', error);
    },
  });
};
