// CQRS Query Hooks - Para operações de leitura
import { useQuery } from '@tanstack/react-query';
import {
  getMediaById,
  getMediaByUser,
  getTranscriptionByMediaId,
  getTranscriptionById,
  getTextAnalysisByMediaId,
  getCurrentUser,
  getSystemStats,
  getAllUsers,
  getAllMediaAdmin,
  getMediaStats,
} from '@/api/queries';

// =============================================================================
// MEDIA QUERIES
// =============================================================================

export const useMediaByIdQuery = (mediaId: string) => {
  return useQuery({
    queryKey: ['media', mediaId],
    queryFn: () => getMediaById(mediaId),
    enabled: !!mediaId,
    staleTime: 30000,
    refetchOnWindowFocus: false,
  });
};

export const useMediaByUserQuery = (
  page: number = 1,
  limit: number = 100,
  order: 'asc' | 'desc' = 'desc',
  search: string = ""
) => {
  return useQuery({
    queryKey: ['media-list', page, limit, order, search],
    queryFn: () => getMediaByUser(page, limit, order, search),
    staleTime: 60000, // 1 minuto
  });
};

export const useMediaStatsQuery = () => {
  return useQuery({
    queryKey: ['media-stats'],
    queryFn: getMediaStats,
    staleTime: 60000,
    refetchOnWindowFocus: false,
  });
};

// =============================================================================
// TRANSCRIPTION QUERIES
// =============================================================================

export const useTranscriptionByMediaIdQuery = (mediaId: string) => {
  return useQuery({
    queryKey: ['transcription', mediaId],
    queryFn: () => getTranscriptionByMediaId(mediaId),
    enabled: !!mediaId,
    retry: (failureCount, error: any) => {
      // Não fazer retry se for 404 ou 202 (ainda processando)
      if (error?.response?.status === 404 || error?.response?.status === 202) {
        return false;
      }
      return failureCount < 3;
    },
    refetchOnWindowFocus: false,
  });
};

export const useTranscriptionByIdQuery = (transcriptionId: string) => {
  return useQuery({
    queryKey: ['transcription', transcriptionId],
    queryFn: () => getTranscriptionById(transcriptionId),
    enabled: !!transcriptionId,
  });
};

// =============================================================================
// TEXT ANALYSIS QUERIES (unificado)
// =============================================================================

export const useTextAnalysisByMediaIdQuery = (mediaId: string) => {
  return useQuery({
    queryKey: ['text-analysis', mediaId],
    queryFn: () => getTextAnalysisByMediaId(mediaId),
    enabled: !!mediaId,
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404) {
        return false;
      }
      return failureCount < 3;
    },
    refetchOnWindowFocus: false,
  });
};

// =============================================================================
// AUTH QUERIES
// =============================================================================

export const useCurrentUserQuery = () => {
  return useQuery({
    queryKey: ['current-user'],
    queryFn: getCurrentUser,
    staleTime: 5 * 60 * 1000, // 5 minutos
    retry: false,
  });
};

// =============================================================================
// NOTIFICATION QUERIES
// =============================================================================

// Notificações via WebSocket (ver contexts/WebSocketContext)

// =============================================================================
// ADMIN QUERIES
// =============================================================================

export const useSystemStatsQuery = () => {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: getSystemStats,
    refetchOnWindowFocus: false,
  });
};

export const useAllUsersQuery = () => {
  return useQuery({
    queryKey: ['admin', 'users'],
    queryFn: getAllUsers,
    staleTime: 2 * 60 * 1000, // 2 minutos
  });
};

export const useAllMediaAdminQuery = () => {
  return useQuery({
    queryKey: ['admin', 'media'],
    queryFn: getAllMediaAdmin,
    staleTime: 60000, // 1 minuto
  });
};

// =============================================================================
// UTILITY HOOKS
// =============================================================================

// Hook combinado para buscar todos os dados de uma mídia
export const useMediaDetailQuery = (mediaId: string) => {
  const mediaQuery = useMediaByIdQuery(mediaId);
  const transcriptionQuery = useTranscriptionByMediaIdQuery(mediaId);
  const textAnalysisQuery = useTextAnalysisByMediaIdQuery(mediaId);

  return {
    media: mediaQuery,
    transcription: transcriptionQuery,
    text_analysis: textAnalysisQuery,
    isLoading: mediaQuery.isLoading,
    hasError: mediaQuery.isError,
  };
};
