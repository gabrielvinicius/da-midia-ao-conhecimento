import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

export const useStorageProviders = () => {
  return useQuery({
    queryKey: ['storageProviders'],
    queryFn: async (): Promise<string[]> => {
      const response = await api.get<string[]>('/providers/storage');
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};