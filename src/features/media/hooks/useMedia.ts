import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { listMedia, getMediaById, uploadMedia, reprocessMedia, UploadMediaParams } from '../api';

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
    refetchInterval: (query) => {
      // Poll for updates only if the media is in a processing state
      const media = query.state.data;
      return media?.status === 'PROCESSING' ? 5000 : false;
    },
  });
};

// Hook for the media upload mutation
export const useUploadMedia = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: UploadMediaParams) => uploadMedia(params),
    onSuccess: (data) => {
      console.log('Upload successful:', data);
      const filename = data.original_file_path?.split('/').pop() || 'arquivo';
      toast.success(`Arquivo "${filename}" enviado com sucesso! O processamento foi iniciado.`);
      queryClient.invalidateQueries({ queryKey: ['mediaList'] });
      navigate('/dashboard');
    },
    onError: (error: any) => {
      console.error('Upload failed:', error);
      
      // Extrai a mensagem de erro mais específica
      let errorMessage = 'Erro ao fazer upload do arquivo';
      
      if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error?.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error?.message) {
        errorMessage = error.message;
      }
      
      toast.error(errorMessage);
    },
  });
};

// Hook for the media reprocess mutation
export const useReprocessMedia = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mediaId: string) => reprocessMedia(mediaId),
    onSuccess: (data, mediaId) => {
      toast.info(data.message);
      // Invalidate queries to refetch media status and list
      queryClient.invalidateQueries({ queryKey: ['mediaDetail', mediaId] });
      queryClient.invalidateQueries({ queryKey: ['mediaList'] });
    },
    onError: (error) => {
      console.error('Reprocess failed:', error);
    },
  });
};
