import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { isInProgress, MediaStatus } from '@/types';

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
  statuses: MediaStatus[] = [],
) =>
  useQuery({
    queryKey: ['media-list', page, limit, order, search, statuses],
    queryFn: () => listMedia(page, limit, order, search, statuses),
    staleTime: 60000,
    // Troca de página ou de filtro sem piscar a lista inteira.
    placeholderData: keepPreviousData,
    // Com mídias em andamento, a lista se atualiza sozinha (o aviso em tempo
    // real também atualiza, mas pode cair).
    refetchInterval: (query) =>
      query.state.data?.items.some((m) => m.status === MediaStatus.UPLOADED || isInProgress(m.status)) ? 15000 : false,
  });

export const useMediaStatsQuery = () =>
  useQuery({
    queryKey: ['media-stats'],
    queryFn: getMediaStats,
    staleTime: 60000,
    refetchInterval: (query) => {
      const byStatus = query.state.data?.by_status ?? {};
      const active = ['uploaded', 'processing', 'analyzing'].some((s) => (byStatus[s] ?? byStatus[s.toUpperCase()] ?? 0) > 0);
      return active ? 15000 : false;
    },
    refetchOnWindowFocus: false,
  });

export const useAnalysisEstimationQuery = (mediaId: string, enabled = true) =>
  useQuery({
    queryKey: ['analysis-estimation', mediaId],
    queryFn: () => getAnalysisEstimation(mediaId),
    enabled: !!mediaId && enabled,
    staleTime: 30000,
  });
