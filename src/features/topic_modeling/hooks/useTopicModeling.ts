import { useQuery } from '@tanstack/react-query';
import { getTopicModeling } from '../api';

export const useTopicModeling = (mediaId: string) => {
  return useQuery({
    queryKey: ['topic-modeling', mediaId],
    queryFn: () => getTopicModeling(mediaId),
    enabled: !!mediaId,
    retry: (failureCount, error: any) => {
      // Não fazer retry se for 404 (análise ainda não processada)
      if (error?.response?.status === 404) {
        return false;
      }
      return failureCount < 3;
    },
    refetchInterval: (query) => {
      // Se deu erro 404, tentar novamente a cada 10 segundos
      if (query.state.error?.response?.status === 404) {
        return 10000;
      }
      // Se não tem dados ainda, verificar a cada 10 segundos
      return !query.state.data ? 10000 : false;
    },
  });
};
