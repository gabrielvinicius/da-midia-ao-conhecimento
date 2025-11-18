import axios from 'axios';
import { toast } from 'react-toastify';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor to add the auth token to headers
api.interceptors.request.use(
  (config) => {
    // Nada para anexar: cookies httpOnly já viajam por withCredentials
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
    console.log('✅ Response recebido:', {
      url: response.config.url,
      status: response.status,
      method: response.config.method
    });
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    const message = error.response?.data?.message || error.response?.data?.detail || error.message || 'Erro desconhecido';
    
    console.error('❌ Erro na API:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: message
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
