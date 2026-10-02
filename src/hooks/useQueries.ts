// CQRS Query Hooks - Para operações de leitura
import { useQuery } from '@tanstack/react-query';
import { apiErrorStatus } from '@/lib/errors';
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
  ProvidersResponse,
  getProviders,
  AnalysisEstimation,
  getAnalysisEstimation,
  getSystemStatus,
  SystemStatusResponse,
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

// =============================================================================
// TEXT ANALYSIS QUERIES (unificado)
// =============================================================================

export const useTextAnalysisByMediaIdQuery = (mediaId: string) => {
  return useQuery({
    queryKey: ['text-analysis', mediaId],
    queryFn: () => getTextAnalysisByMediaId(mediaId),
    enabled: !!mediaId,
    retry: (failureCount, error) => apiErrorStatus(error) !== 404 && failureCount < 3,
    refetchOnWindowFocus: false,
  });
};

// =============================================================================
// AUTH QUERIES
// =============================================================================

// =============================================================================
// NOTIFICATION QUERIES
// =============================================================================

// Notificações via WebSocket (ver contexts/WebSocketContext)

// =============================================================================
// ADMIN QUERIES
// =============================================================================

// =============================================================================
// UTILITY HOOKS
// =============================================================================

// Hook combinado para buscar todos os dados de uma mídia
export const useAnalysisEstimationQuery = (mediaId: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ['analysis-estimation', mediaId],
    queryFn: () => getAnalysisEstimation(mediaId),
    enabled: !!mediaId && enabled,
    staleTime: 1000 * 30, // 30 seconds
  });
};

export const useSystemStatusQuery = () => {
  return useQuery({
    queryKey: ['system-status'],
    queryFn: getSystemStatus,
    refetchInterval: 30000, // Poll every 30 seconds
    staleTime: 25000,
  });
};
