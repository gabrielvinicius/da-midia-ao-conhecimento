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
  getStorageProviders,
  getTranscriptionProviders,
  getSummarizationProviders,
  getAllProviders,
  getNotifications,
  getSystemStats,
  getAllUsers,
  getAllMediaAdmin,
} from '@/api/queries';

// =============================================================================
// MEDIA QUERIES
// =============================================================================

export const useMediaByIdQuery = (mediaId: string) => {
  return useQuery({
    queryKey: ['media', mediaId],
    queryFn: () => getMediaById(mediaId),
    enabled: !!mediaId,
    staleTime: 30000, // 30 segundos
    refetchInterval: (query) => {
      // Polling para media em processamento
      const media = query.state.data;
      return media?.status === 'PROCESSING' ? 5000 : false;
    },
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
    refetchInterval: (query) => {
      // Se deu erro 404/202, tentar novamente a cada 10 segundos
      const error = query.state.error as any;
      if (error?.response?.status === 404 || error?.response?.status === 202) {
        return 10000;
      }
      return false;
    },
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
    refetchInterval: (query) => {
      const error = query.state.error as any;
      if (error?.response?.status === 404 || error?.response?.status === 202) {
        return 10000;
      }
      return false;
    },
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
    refetchInterval: (query) => (!query.state.data ? 10000 : false),
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
    refetchInterval: (query) => (!query.state.data ? 10000 : false),
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

export const useStorageProvidersQuery = () => {
  return useQuery({
    queryKey: ['providers', 'storage'],
    queryFn: getStorageProviders,
    staleTime: 10 * 60 * 1000, // 10 minutos (providers raramente mudam)
  });
};

export const useTranscriptionProvidersQuery = () => {
  return useQuery({
    queryKey: ['providers', 'transcription'],
    queryFn: getTranscriptionProviders,
    staleTime: 10 * 60 * 1000,
  });
};

export const useSummarizationProvidersQuery = () => {
  return useQuery({
    queryKey: ['providers', 'summarization'],
    queryFn: getSummarizationProviders,
    staleTime: 10 * 60 * 1000,
  });
};

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
    refetchInterval: 30000, // Refetch a cada 30 segundos para notificações
  });
};

// =============================================================================
// ADMIN QUERIES
// =============================================================================

export const useSystemStatsQuery = () => {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: getSystemStats,
    refetchInterval: 60000, // Refetch a cada 1 minuto para estatísticas
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
