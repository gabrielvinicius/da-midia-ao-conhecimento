import { useQuery } from '@tanstack/react-query';
import {
  getSystemStats,
  getSystemPerformanceMetrics,
  getProcessingTrends,
  getSystemHealth,
  getMediaProcessingStats,
  getMetricsSummary,
  getBusinessKpis,
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

export const useSystemPerformance = (timeRange: string = 'last_week', enabled = true) => {
  return useQuery({
    queryKey: ['admin-system-performance', timeRange],
    queryFn: () => getSystemPerformanceMetrics(timeRange),
    staleTime: 60_000,
    enabled,
    retry: enabled,
  });
};

export const useProcessingTrends = (days: number = 30, enabled = true) => {
  return useQuery({
    queryKey: ['admin-processing-trends', days],
    queryFn: () => getProcessingTrends(days),
    staleTime: 60_000,
    enabled,
    retry: enabled,
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

export const useMediaProcessingStats = (enabled = true) => {
  return useQuery({
    queryKey: ['admin-media-processing-stats'],
    queryFn: getMediaProcessingStats,
    staleTime: 30_000,
    enabled,
  });
};

export const useMetricsSummary = (enabled = true) => {
  return useQuery({
    queryKey: ['admin-metrics-summary'],
    queryFn: getMetricsSummary,
    enabled,
  });
};

export const useBusinessKpis = (enabled: boolean = true) => {
  return useQuery({
    queryKey: ['admin-business-kpis'],
    queryFn: getBusinessKpis,
    enabled,
    retry: false,
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
  });
};
