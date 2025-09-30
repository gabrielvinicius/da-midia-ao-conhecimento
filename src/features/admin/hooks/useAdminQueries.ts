import { useQuery } from '@tanstack/react-query';
import { getSystemStats, getAllUsers, getAllMedia } from '../api';

export const useSystemStats = () => {
  return useQuery({
    queryKey: ['admin-stats'],
    queryFn: getSystemStats,
  });
};

export const useAllUsers = () => {
  return useQuery({
    queryKey: ['admin-all-users'],
    queryFn: getAllUsers,
  });
};

export const useAllMedia = () => {
  return useQuery({
    queryKey: ['admin-all-media'],
    queryFn: getAllMedia,
  });
};
