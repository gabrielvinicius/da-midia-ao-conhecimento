// CQRS Query Hooks - Para operações de leitura
import { useQuery } from '@tanstack/react-query';
import {
  getMediaById,
  getMediaByUser,
  getTranscriptionByMediaId,
  getTranscriptionById,
  getSummaryByMediaId,
  getSummaryById,
  getSentimentAnalysisByMediaId,
  getTopicModelingByMediaId,
  getCurrentUser,
  getAllProviders,
  getNotifications,
  getSystemStats,
  getAllUsers,
  getAllMediaAdmin,
} from '@/api/queries';
import { useProviders } from '@/features/providers/hooks/useProviders';
import { useStorageProviders } from '@/features/providers/hooks/useStorageProviders';

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

export const useMediaByUserQuery = () => {
  return useQuery({
    queryKey: ['media-list'],
    queryFn: getMediaByUser,
    staleTime: 60000, // 1 minuto
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
// SUMMARIZATION QUERIES
// =============================================================================

export const useSummaryByMediaIdQuery = (mediaId: string) => {
  return useQuery({
    queryKey: ['summary', mediaId],
    queryFn: () => getSummaryByMediaId(mediaId),
    enabled: !!mediaId,
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 202) {
        return false;
      }
      return failureCount < 3;
    },
    refetchOnWindowFocus: false,
  });
};

export const useSummaryByIdQuery = (summaryId: string) => {
  return useQuery({
    queryKey: ['summary', summaryId],
    queryFn: () => getSummaryById(summaryId),
    enabled: !!summaryId,
  });
};

// =============================================================================
// SENTIMENT ANALYSIS QUERIES
// =============================================================================

export const useSentimentAnalysisByMediaIdQuery = (mediaId: string) => {
  return useQuery({
    queryKey: ['sentiment-analysis', mediaId],
    queryFn: () => getSentimentAnalysisByMediaId(mediaId),
    enabled: !!mediaId,
    refetchOnWindowFocus: false,
  });
};

// =============================================================================
// TOPIC MODELING QUERIES
// =============================================================================

export const useTopicModelingByMediaIdQuery = (mediaId: string) => {
  return useQuery({
    queryKey: ['topic-modeling', mediaId],
    queryFn: () => getTopicModelingByMediaId(mediaId),
    enabled: !!mediaId,
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
// PROVIDER QUERIES
// =============================================================================

export const useStorageProvidersQuery = useStorageProviders;
export const useTranscriptionProvidersQuery = () => useProviders('transcription');
export const useSummarizationProvidersQuery = () => useProviders('summarization');

export const useAllProvidersQuery = () => {
  return useQuery({
    queryKey: ['providers', 'all'],
    queryFn: getAllProviders,
    staleTime: 10 * 60 * 1000,
  });
};

// =============================================================================
// NOTIFICATION QUERIES
// =============================================================================

export const useNotificationsQuery = () => {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: getNotifications,
    refetchOnWindowFocus: false,
  });
};

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
  const summaryQuery = useSummaryByMediaIdQuery(mediaId);
  const sentimentQuery = useSentimentAnalysisByMediaIdQuery(mediaId);
  const topicQuery = useTopicModelingByMediaIdQuery(mediaId);

  return {
    media: mediaQuery,
    transcription: transcriptionQuery,
    summary: summaryQuery,
    sentiment: sentimentQuery,
    topics: topicQuery,
    isLoading: mediaQuery.isLoading,
    hasError: mediaQuery.isError,
  };
};

// Hook para buscar providers necessários no upload
export const useUploadProvidersQuery = () => {
  const storageQuery = useStorageProvidersQuery();
  const transcriptionQuery = useTranscriptionProvidersQuery();
  const summarizationQuery = useSummarizationProvidersQuery();

  return {
    storage: storageQuery,
    transcription: transcriptionQuery,
    summarization: summarizationQuery,
    isLoading: storageQuery.isLoading || transcriptionQuery.isLoading || summarizationQuery.isLoading,
    hasError: storageQuery.isError || transcriptionQuery.isError || summarizationQuery.isError,
  };
};
