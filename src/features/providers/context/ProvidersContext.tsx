import { createContext, useContext, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getProvidersMap, ProviderType } from '../api';
import { useAuth } from '@/contexts/AuthContext';

type ProviderMap = Partial<Record<ProviderType, string[]>>;

interface ProvidersContextValue {
  providers: Partial<ProviderMap>;
  isLoading: boolean;
  error: unknown;
}

const ProvidersContext = createContext<ProvidersContextValue | undefined>(undefined);

export const ProvidersProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const result = useQuery({
    queryKey: ['providers', 'map'],
    queryFn: async () => {
      const map = await getProvidersMap();
      return map as ProviderMap;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 401) {
        return false;
      }
      return failureCount < 3;
    },
  });

  const value = useMemo<ProvidersContextValue>(
    () => ({ providers: result.data || {}, isLoading: result.isLoading, error: result.error }),
    [result.data, result.isLoading, result.error],
  );

  return <ProvidersContext.Provider value={value}>{children}</ProvidersContext.Provider>;
};

export const useProvidersContext = () => {
  const ctx = useContext(ProvidersContext);
  if (!ctx) {
    throw new Error('useProvidersContext must be used inside ProvidersProvider');
  }
  return ctx;
};

export const useProviderList = (type: ProviderType) => {
  const { providers, isLoading, error } = useProvidersContext();
  return {
    data: providers[type] || [],
    isLoading,
    error,
  };
};
