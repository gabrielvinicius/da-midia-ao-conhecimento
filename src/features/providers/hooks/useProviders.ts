import { useQuery } from '@tanstack/react-query';
import { getProviders, ProviderType } from '../api';

export const useProviders = (type: ProviderType) => {
  return useQuery({
    queryKey: ['providers', type],
    queryFn: () => getProviders(type),
    staleTime: Infinity, // Provider list is static, no need to refetch
  });
};
