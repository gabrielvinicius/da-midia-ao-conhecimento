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

/**
 * O que o cliente HTTP precisa da sessão. O authService se registra aqui
 * (bindSession), e este módulo não o importa (evita a dependência circular).
 */
export interface SessionPort {
  getToken(): string | null;
  hasSession(): boolean;
  refreshSession(): Promise<boolean>;
  clearLocalAuth(): void;
}

let session: SessionPort | null = null;

export const bindSession = (port: SessionPort): void => {
  session = port;
};

const api = axios.create({
  withCredentials: false,
});

api.interceptors.request.use((config) => {
  if (!config.baseURL) {
    config.baseURL = getApiBaseUrl();
  }
  const token = session?.getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

const AUTH_ENDPOINTS = ['/auth/token', '/auth/refresh', '/auth/logout'];

/**
 * Só o que é global fica aqui: renovar a sessão num 401, avisar quando ela
 * acabou, e os erros que nenhuma tela trata (rede, servidor, arquivo grande).
 * Os demais (400, 404, 409, 422) são de quem chamou: antes, este interceptador
 * avisava todo 404, e a tela de uma mídia ainda sem análise mostrava "Não
 * encontrado" enquanto a análise estava a caminho.
 */
const isRead = (config?: { method?: string }) => !config?.method || config.method.toLowerCase() === 'get';

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status: number | undefined = error.response?.status;
    const original = error.config;
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => original?.url?.includes(path));

    if (status === 401 && !isAuthEndpoint && original && !original._retry && session) {
      original._retry = true;
      const hadSession = session.hasSession();
      if (hadSession && (await session.refreshSession())) {
        return api.request(original);
      }
      session.clearLocalAuth();
      if (hadSession) {
        // Visitante sem sessão não recebe aviso: antes, abrir a tela de login
        // mostrava "Sessão expirada".
        toast.error('Sessão expirada. Faça login novamente.', { toastId: 'session-expired' });
        window.dispatchEvent(new CustomEvent('app:logout'));
      }
    } else if (!isRead(original)) {
      // Gravações (POST, PUT, DELETE) mostram o próprio erro: toda mutação tem
      // onError, e o envio mostra a falha no item. Com o aviso daqui também,
      // o mesmo erro aparecia duas vezes.
    } else if (status !== undefined && status >= 500) {
      toast.error('Erro no servidor. Tente novamente em instantes.', { toastId: 'server-error' });
    } else if (!error.response) {
      toast.error('Sem conexão com o servidor. Verifique a sua internet.', { toastId: 'network-error' });
    }
    return Promise.reject(error);
  }
);

export default api;
