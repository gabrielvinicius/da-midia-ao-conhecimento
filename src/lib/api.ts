import axios from 'axios';
import { toast } from 'react-toastify';

const normalizeBase = (value: string) => value.replace(/\/$/, '');
const ensureAbsolutePath = (path: string): string => (path.startsWith('/') ? path : `/${path}`);

const envConfiguredBase = () => {
  const configured = (import.meta.env.VITE_API_URL || '').trim();
  return configured ? normalizeBase(configured) : '';
};

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

  const forced = import.meta.env.VITE_FORCE_API_URL === 'true';
  const configured = envConfiguredBase();

  const origin = runtimeOrigin();
  if (origin && (!import.meta.env.PROD || !forced)) {
    cachedBaseUrl = `${origin}${API_PREFIX}`;
    return cachedBaseUrl;
  }

  cachedBaseUrl = configured || 'http://localhost:8000';
  return cachedBaseUrl;
};

if (typeof window !== 'undefined') {
  const origin = runtimeOrigin();
  if (origin) {
    cachedBaseUrl = `${origin}${API_PREFIX}`;
  }
}

export const buildApiUrl = (path = '/'): string => `${getApiBaseUrl()}${ensureAbsolutePath(path)}`;
export const buildWsUrl = (path = '/'): string => buildApiUrl(path).replace(/^http/, 'ws');

const api = axios.create({
  withCredentials: true,
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
    console.log('✅ Response recebido:', {
      url: response.config.url,
      status: response.status,
      method: response.config.method,
      correlationId: correlationId
    });
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
    
    // Se erro 401 e não é uma requisição de auth, tentar refresh
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest.url?.includes('/auth/token') &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;
      console.log('🔄 Tentando refresh automático com cookies...');

      try {
        const { default: authService } = await import('../services/auth.service');
        await authService.refreshToken();
        console.log('✅ Sessão renovada, repetindo requisição original');
        return api.request(originalRequest);
      } catch (refreshError) {
        console.error('❌ Refresh token falhou:', refreshError);
        const { default: authService } = await import('../services/auth.service');
        authService.clearLocalAuth();
        toast.error('Sessão expirada. Faça login novamente.');
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    if (error.response?.status === 401) {
      console.warn('🔐 Sessão inválida ou expirada');
      const { default: authService } = await import('../services/auth.service');
      authService.clearLocalAuth();
      toast.error('Sessão expirada. Faça login novamente.');

      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
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