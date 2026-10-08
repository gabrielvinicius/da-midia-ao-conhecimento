import { useQuery } from '@tanstack/react-query';

import { getAnalysisEstimation, getMedia, getMediaStats, listMedia } from '../api';

export const useMediaByIdQuery = (mediaId: string) =>
  useQuery({
    queryKey: ['media', mediaId],
    queryFn: () => getMedia(mediaId),
    enabled: !!mediaId,
    staleTime: 30000,
    refetchOnWindowFocus: false,
  });

export const useMediaByUserQuery = (
  page = 1,
  limit = 100,
  order: 'asc' | 'desc' = 'desc',
  search = '',
) =>
  useQuery({
    queryKey: ['media-list', page, limit, order, search],
    queryFn: () => listMedia(page, limit, order, search),
    staleTime: 60000,
  });

export const useMediaStatsQuery = () =>
  useQuery({
    queryKey: ['media-stats'],
    queryFn: getMediaStats,
    staleTime: 60000,
    refetchOnWindowFocus: false,
  });

export const useAnalysisEstimationQuery = (mediaId: string, enabled = true) =>
  useQuery({
    queryKey: ['analysis-estimation', mediaId],
    queryFn: () => getAnalysisEstimation(mediaId),
    enabled: !!mediaId && enabled,
    staleTime: 30000,
  });
