import { useQuery } from '@tanstack/react-query';

import { apiErrorStatus } from '@/lib/errors';
import { getAnalysisByMediaId } from '../api';

/** Análise da mídia (null enquanto não existe); compartilhada pelos painéis. */
export const useTextAnalysisByMediaIdQuery = (mediaId: string) =>
  useQuery({
    queryKey: ['text-analysis', mediaId],
    queryFn: () => getAnalysisByMediaId(mediaId),
    enabled: !!mediaId,
    retry: (failureCount, error) => apiErrorStatus(error) !== 404 && failureCount < 3,
    refetchOnWindowFocus: false,
  });
