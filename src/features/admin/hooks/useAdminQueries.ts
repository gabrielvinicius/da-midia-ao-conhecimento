import { useQuery } from '@tanstack/react-query';
import { getSystemStats, getAllUsers, getAllMedia, GetPaginatedDataParams } from '../api';

export const useSystemStats = () => {
  return useQuery({
    queryKey: ['admin-stats'],
    queryFn: getSystemStats,
  });
};

export const useAllUsers = (params: GetPaginatedDataParams) => {
  return useQuery({
    // The query will refetch automatically when page, limit, or search changes
    queryKey: ['admin-all-users', params.page, params.limit, params.search],
    queryFn: () => getAllUsers(params),
    keepPreviousData: true, // Provides a smoother UX during pagination
  });
};

export const useAllMedia = (params: GetPaginatedDataParams) => {
  return useQuery({
    queryKey: ['admin-all-media', params.page, params.limit, params.search],
    queryFn: () => getAllMedia(params),
    keepPreviousData: true,
  });
};
