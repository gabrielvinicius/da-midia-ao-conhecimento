import axios from 'axios';
import { toast } from 'react-toastify';

const normalizeBase = (value: string) => value.replace(/\/$/, '');
const ensureAbsolutePath = (path: string): string => (path.startsWith('/') ? path : `/${path}`);

const envConfiguredBase = () => {
  const configured = (import.meta.env.VITE_API_URL || '').trim();
  return configured ? normalizeBase(configured) : '';
};

// Em Docker (nginx), a API é exposta sob /api e proxied para o backend.
const API_PREFIX = "/api";

const runtimeOrigin = (): string | undefined => {
  if (typeof window === 'undefined') {
    return undefined;
  }
  try {
    return window.location?.origin ? normalizeBase(window.location.origin) : undefined;
  } catch (error) {
    console.warn('Não foi possível ler window.location.origin', error);
    return undefined;
  }
};

let cachedBaseUrl: string | null = null;

export const getApiBaseUrl = (): string => {
  if (cachedBaseUrl) {
    return cachedBaseUrl;
  }

  const configured = envConfiguredBase();

  const origin = runtimeOrigin();
  // Produção (Docker/nginx): preferir origin + /api para usar o reverse proxy.
  if (origin && import.meta.env.PROD) {
    cachedBaseUrl = `${origin}${API_PREFIX}`;
    return cachedBaseUrl;
  }

  // Desenvolvimento: se configurado, usa VITE_API_URL (útil quando o backend roda em outra porta).
  if (configured) {
    cachedBaseUrl = configured;
    return cachedBaseUrl;
  }

  if (origin) {
    cachedBaseUrl = `${origin}${API_PREFIX}`;
    return cachedBaseUrl;
  }

  cachedBaseUrl = 'http://localhost:8000';
  return cachedBaseUrl;
};

if (typeof window !== 'undefined') {
  const origin = runtimeOrigin();
  if (origin) {
    const configured = envConfiguredBase();
    if (import.meta.env.PROD || !configured) {
      cachedBaseUrl = `${origin}${API_PREFIX}`;
    }
  }
}

export const buildApiUrl = (path = '/'): string => `${getApiBaseUrl()}${ensureAbsolutePath(path)}`;
export const buildWsUrl = (path = '/'): string => buildApiUrl(path).replace(/^http/, 'ws');

const api = axios.create({
  withCredentials: false,
});

// Request interceptor to add the auth token to headers
api.interceptors.request.use(
  (config) => {
    if (!config.baseURL) {
      config.baseURL = getApiBaseUrl();
    }
    const token = sessionStorage.getItem('access_token');
    if (token) {
      config.headers = config.headers ?? {};
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('❌ Erro no request interceptor:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for global error handling and token refresh
api.interceptors.response.use(
  (response) => {
    const correlationId = response.headers['x-correlation-id'];
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    const correlationId = error.response?.headers['x-correlation-id'];
    const message = error.response?.data?.message || error.response?.data?.detail || error.message || 'Erro desconhecido';
    
    console.error('❌ Erro na API:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: message,
      correlationId: correlationId
    });
    
    const isAuthEndpoint =
      originalRequest?.url?.includes('/auth/token') ||
      originalRequest?.url?.includes('/auth/refresh');

    if (error.response?.status === 401 && !isAuthEndpoint) {
      // Evita loops: uma tentativa de refresh por request
      if (!originalRequest?._retry) {
        originalRequest._retry = true;
        try {
          await authService.refreshToken();
          const newToken = sessionStorage.getItem('access_token');
          if (newToken) {
            originalRequest.headers = originalRequest.headers ?? {};
            originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
          }
          return api.request(originalRequest);
        } catch (refreshError) {
          console.warn('🔐 Refresh falhou, limpando sessão');
        }
      }
      authService.clearLocalAuth();
      toast.error('Sessão expirada. Faça login novamente.');
      // Sinaliza para a SPA redirecionar sem recarregar
      const logoutEvent = new CustomEvent('app:logout');
      window.dispatchEvent(logoutEvent);
    } else if (error.response?.status === 413) {
      toast.error('Arquivo muito grande. Tamanho máximo permitido: 200MB');
    } else if (error.response?.status === 400) {
      toast.error(`Dados inválidos: ${message}`);
    } else if (error.response?.status === 403) {
      toast.error('Acesso negado. Verifique suas permissões.');
    } else if (error.response?.status === 404) {
        // 404 specific handling might be needed, but general toast is often enough
        toast.error(`Não encontrado: ${message}`);
    } else if (error.response?.status === 409) {
        toast.error(`Conflito: ${message}`);
    } else if (error.response?.status === 500) {
      toast.error('Erro interno do servidor. Tente novamente.');
    } else if (error.code === 'NETWORK_ERROR' || !error.response) {
      toast.error('Erro de conexão. Verifique sua internet.');
    } else {
      toast.error(message);
    }

    return Promise.reject(error);
  }
);

export default api;
