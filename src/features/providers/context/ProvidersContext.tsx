import { createContext, useContext, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getProviders, ProviderType } from '../api';

type ProviderMap = Record<ProviderType, string[]>;

interface ProvidersContextValue {
  providers: Partial<ProviderMap>;
  isLoading: boolean;
  error: unknown;
}

const ProvidersContext = createContext<ProvidersContextValue | undefined>(undefined);

const providerTypes: ProviderType[] = [
  'storage',
  'transcription',
  'summarization',
  'sentiment',
  'topics',
];

export const ProvidersProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const result = useQuery({
    queryKey: ['providers', 'all'],
    queryFn: async () => {
      const entries = await Promise.all(
        providerTypes.map(async (type) => {
          const data = await getProviders(type);
          return [type, data] as const;
        })
      );
      return Object.fromEntries(entries) as ProviderMap;
    },
    staleTime: Infinity,
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
