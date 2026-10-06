import { useQuery } from '@tanstack/react-query';

import api from '@/lib/api';

/** Nível de carga para todos; os números só vêm para administradores. */
export type SystemStatusResponse = {
  pressure: 'low' | 'moderate' | 'high' | 'critical';
  cpu_usage?: number;
  ram_usage?: number;
  gpu_vram_usage?: number | null;
};

export const getSystemStatus = async (): Promise<SystemStatusResponse> =>
  (await api.get<SystemStatusResponse>('/monitoring/system-status')).data;

export const useSystemStatusQuery = () =>
  useQuery({
    queryKey: ['system-status'],
    queryFn: getSystemStatus,
    refetchInterval: 30000,
    staleTime: 25000,
  });
