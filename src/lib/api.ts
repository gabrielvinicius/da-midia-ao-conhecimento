import axios from 'axios';
import { toast } from 'react-toastify';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * @deprecated Use secureApi from './secure-api.ts' instead
 * This legacy API client is kept for backward compatibility
 */
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add the auth token to headers
api.interceptors.request.use(
  (config) => {
    // Buscar token do localStorage
    const token = localStorage.getItem('token');
    if (token) {
      // Garantir que o header Authorization existe
      if (!config.headers) {
        config.headers = {};
      }
      config.headers.Authorization = `Bearer ${token}`;
      
      console.log('🔑 Token adicionado ao request:', {
        url: config.url,
        method: config.method,
        hasToken: !!token,
        tokenPreview: token.substring(0, 20) + '...'
      });
    } else {
      console.warn('⚠️ Nenhum token encontrado no localStorage para request:', config.url);
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
    if (error.response?.status === 401 && 
        originalRequest && 
        !originalRequest.url?.includes('/auth/token') &&
        !originalRequest.url?.includes('/auth/refresh') &&
        !originalRequest._retry) {
      
      originalRequest._retry = true;
      
      console.log('🔄 Tentando refresh automático do token...');
      
      try {
        // Importar AuthService dinamicamente para evitar dependência circular
        const { default: authService } = await import('../services/auth.service');
        
        // Tentar refresh token
        await authService.refreshToken();
        
        console.log('✅ Token refreshed, repetindo requisição original');
        
        // Repetir a requisição original com o novo token
        return api.request(originalRequest);
        
      } catch (refreshError) {
        console.error('❌ Refresh token falhou:', refreshError);
        
        // Limpar dados de auth e redirecionar
        localStorage.removeItem('token');
        sessionStorage.removeItem('csrf_token');
        toast.error('Sessão expirada. Faça login novamente.');
        
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        
        return Promise.reject(refreshError);
      }
    }
    
    // Tratar outros códigos de status
    if (error.response?.status === 401) {
      console.warn('🔐 Token inválido ou expirado');
      localStorage.removeItem('token');
      sessionStorage.removeItem('csrf_token');
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
