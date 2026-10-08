import { useQuery } from '@tanstack/react-query';
import { getAuthOptions } from '../api';

/** O que as telas de entrada oferecem; sem resposta, como se o e-mail estivesse desligado. */
export const useAuthOptions = () =>
  useQuery({
    queryKey: ['auth-options'],
    queryFn: getAuthOptions,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
