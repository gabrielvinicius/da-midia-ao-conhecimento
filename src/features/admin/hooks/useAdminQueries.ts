import { keepPreviousData, useQuery } from '@tanstack/react-query';
import {
  getSystemStats,
  getSystemHealth,
  getMediaProcessingStats,
  getProcessingTimes,
  getAllUsers,
  getAllMedia,
  GetPaginatedDataParams,
} from '../api';

export const useSystemStats = () => {
  return useQuery({
    queryKey: ['admin-stats'],
    queryFn: getSystemStats,
  });
};

export const useSystemHealth = (enabled = true) => {
  return useQuery({
    queryKey: ['admin-stats-health'],
    queryFn: getSystemHealth,
    staleTime: 60_000,
    enabled,
  });
};

export const useProcessingTimes = (days?: number, enabled = true) => {
  return useQuery({
    queryKey: ['admin-processing-times', days ?? 'all'],
    queryFn: () => getProcessingTimes(days),
    staleTime: 30_000,
    enabled,
  });
};

export const useMediaProcessingStats = (enabled = true) => {
  return useQuery({
    queryKey: ['admin-media-processing-stats'],
    queryFn: getMediaProcessingStats,
    staleTime: 30_000,
    enabled,
  });
};

export const useAllUsers = (params: GetPaginatedDataParams) => {
  return useQuery({
    // The query will refetch automatically when page, limit, or search changes
    queryKey: ['admin-all-users', params.page, params.limit, params.search],
    queryFn: () => getAllUsers(params),
  });
};

export const useAllMedia = (params: GetPaginatedDataParams) => {
  return useQuery({
    queryKey: ['admin-all-media', params.page, params.limit, params.search],
    queryFn: () => getAllMedia(params),
    placeholderData: keepPreviousData, // mantém a página anterior enquanto a próxima carrega
  });
};
