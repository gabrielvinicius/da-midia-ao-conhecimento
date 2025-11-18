// frontend/src/lib/secure-api.ts
/**
 * Cliente API seguro que usa cookies httpOnly ao invés de localStorage
 * Implementa proteção CSRF e refresh automático de tokens
 */

import axios, { AxiosError, AxiosResponse } from 'axios';
import { toast } from 'react-toastify';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Interface para resposta de erro padronizada
interface ApiError {
  error: string;
  message: string;
  details: Record<string, any>;
  timestamp: string;
}

// Interface para resposta de login
interface LoginResponse {
  access_token: string;
  token_type: string;
  csrf_token: string;
}

class SecureApiClient {
  private axiosInstance;
  private csrfToken: string | null = null;
  private isRefreshing = false;
  private refreshPromise: Promise<void> | null = null;

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true, // Importante: envia cookies automaticamente
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor para adicionar CSRF token
    this.axiosInstance.interceptors.request.use(
      (config) => {
        // Adicionar CSRF token para métodos que modificam dados
        if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase() || '')) {
          if (this.csrfToken) {
            config.headers['X-CSRF-Token'] = this.csrfToken;
          }
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor para tratar erros e refresh automático
    this.axiosInstance.interceptors.response.use(
      (response: AxiosResponse) => {
        // Extrair CSRF token se presente na resposta
        const newCsrfToken = response.data?.csrf_token;
        if (newCsrfToken) {
          this.csrfToken = newCsrfToken;
        }
        
        return response;
      },
      async (error: AxiosError<ApiError>) => {
        const originalRequest = error.config;
        
        // Se erro 401 e não é request de login/refresh, tentar refresh
        if (
          error.response?.status === 401 && 
          originalRequest && 
          !originalRequest.url?.includes('/auth/token') &&
          !originalRequest.url?.includes('/auth/refresh') &&
          !this.isRefreshing
        ) {
          return this.handleTokenRefresh(originalRequest);
        }

        // Tratar outros erros
        this.handleApiError(error);
        
        return Promise.reject(error);
      }
    );
  }

  private async handleTokenRefresh(originalRequest: any): Promise<AxiosResponse> {
    if (this.isRefreshing) {
      // Se já estamos refreshing, aguardar
      await this.refreshPromise;
      return this.axiosInstance(originalRequest);
    }

    this.isRefreshing = true;
    
    this.refreshPromise = this.refreshToken().finally(() => {
      this.isRefreshing = false;
      this.refreshPromise = null;
    });

    try {
      await this.refreshPromise;
      // Repetir request original com novo token
      return this.axiosInstance(originalRequest);
    } catch (refreshError) {
      // Se refresh falhou, redirecionar para login
      this.handleAuthenticationFailure();
      throw refreshError;
    }
  }

  private async refreshToken(): Promise<void> {
    try {
      const response = await this.axiosInstance.post('/auth/refresh');
      const data = response.data as LoginResponse;
      
      if (data.csrf_token) {
        this.csrfToken = data.csrf_token;
      }
      
      console.log('Token refreshed successfully');
    } catch (error) {
      console.error('Token refresh failed:', error);
      throw error;
    }
  }

  private handleApiError(error: AxiosError<ApiError>) {
    const apiError = error.response?.data;
    
    if (apiError) {
      // Usar mensagem estruturada da API
      const message = apiError.message || 'Erro desconhecido';
      
      switch (error.response?.status) {
        case 400:
          toast.error(`Dados inválidos: ${message}`);
          break;
        case 401:
          toast.error('Sessão expirada. Faça login novamente.');
          this.handleAuthenticationFailure();
          break;
        case 403:
          toast.error('Acesso negado. Você não tem permissão para esta ação.');
          break;
        case 404:
          toast.error('Recurso não encontrado.');
          break;
        case 422:
          toast.error(`Erro de validação: ${message}`);
          break;
        case 429:
          toast.error('Muitas tentativas. Tente novamente mais tarde.');
          break;
        case 500:
          toast.error('Erro interno do servidor. Tente novamente.');
          break;
        default:
          toast.error(message);
      }
    } else {
      // Erro de rede ou outro erro
      toast.error('Erro de conexão. Verifique sua internet.');
    }
  }

  private handleAuthenticationFailure() {
    // Limpar CSRF token
    this.csrfToken = null;
    
    // Redirecionar para login (sem usar window.location para melhor UX)
    const currentPath = window.location.pathname;
    if (!currentPath.includes('/login')) {
      // Armazenar URL atual para redirect após login
      sessionStorage.setItem('redirectAfterLogin', currentPath);
      window.location.href = '/login';
    }
  }

  // Métodos públicos

  async login(email: string, password: string): Promise<LoginResponse> {
    try {
      const response = await this.axiosInstance.post('/auth/token', {
        username: email,
        password: password
      });
      
      const data = response.data as LoginResponse;
      
      if (data.csrf_token) {
        this.csrfToken = data.csrf_token;
      }
      
      toast.success('Login realizado com sucesso!');
      return data;
      
    } catch (error) {
      // Erro já tratado pelo interceptor
      throw error;
    }
  }

  async logout(): Promise<void> {
    try {
      await this.axiosInstance.post('/auth/logout');
      this.csrfToken = null;
      toast.success('Logout realizado com sucesso!');
      
      // Redirecionar para página inicial
      window.location.href = '/login';
      
    } catch (error) {
      // Mesmo se falhar, limpar dados locais
      this.csrfToken = null;
      console.error('Logout error:', error);
      window.location.href = '/login';
    }
  }

  async getCurrentUser() {
    const response = await this.axiosInstance.get('/auth/me');
    return response.data;
  }

  async changePassword(oldPassword: string, newPassword: string, confirmPassword: string) {
    const response = await this.axiosInstance.put('/auth/me/password', {
      old_password: oldPassword,
      new_password: newPassword,
      confirm_new_password: confirmPassword
    });
    
    toast.success('Senha alterada com sucesso!');
    return response.data;
  }

  // Métodos para mídia
  async uploadMedia(formData: FormData) {
    const response = await this.axiosInstance.post('/media/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getMedia(mediaId: string, includeRelations: boolean = false) {
    const response = await this.axiosInstance.get(`/media/${mediaId}`, {
      params: { include_relations: includeRelations }
    });
    return response.data;
  }

  async getUserMedia(params: {
    page?: number;
    limit?: number;
    status_filter?: string;
    media_type_filter?: string;
    order_by?: string;
    order_desc?: boolean;
  } = {}) {
    const response = await this.axiosInstance.get('/media/', { params });
    return response.data;
  }

  async deleteMedia(mediaId: string) {
    const response = await this.axiosInstance.delete(`/media/${mediaId}`);
    toast.success('Mídia removida com sucesso!');
    return response.data;
  }

  // Métodos para transcrições
  async getTranscription(mediaId: string) {
    const response = await this.axiosInstance.get(`/transcriptions/`, {
      params: { media_id: mediaId }
    });
    return response.data;
  }

  async updateSpeakerAliases(transcriptionId: string, aliases: Record<string, string>) {
    const response = await this.axiosInstance.put(`/transcriptions/${transcriptionId}/speakers`, {
      speaker_aliases: aliases
    });
    return response.data;
  }

  // Métodos para resumos
  async getSummary(mediaId: string) {
    const response = await this.axiosInstance.get(`/summaries/`, {
      params: { media_id: mediaId }
    });
    return response.data;
  }

  // Métodos para análise de sentimento
  async getSentimentAnalysis(mediaId: string) {
    try {
      const response = await this.axiosInstance.get(`/sentiment-analysis/`, {
        params: { media_id: mediaId }
      });
      return response.data;
    } catch (error: any) {
      if (error?.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }

  // Métodos para topic modeling
  async getTopicModeling(mediaId: string) {
    try {
      const response = await this.axiosInstance.get(`/topic-modeling/`, {
        params: { media_id: mediaId }
      });
      return response.data;
    } catch (error: any) {
      if (error?.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }

  // Métodos para notificações
  async getNotifications(page: number = 1, limit: number = 20) {
    const response = await this.axiosInstance.get('/notifications/', {
      params: { page, limit }
    });
    return response.data;
  }

  async markNotificationAsRead(notificationId: string) {
    const response = await this.axiosInstance.put(`/notifications/${notificationId}/read`);
    return response.data;
  }

  // Getter para verificar se está autenticado
  get isAuthenticated(): boolean {
    return this.csrfToken !== null;
  }

  // Getter para CSRF token (para uso em WebSockets, etc.)
  get csrfTokenValue(): string | null {
    return this.csrfToken;
  }
}

// Instância singleton
export const secureApi = new SecureApiClient();

// Export como default também
export default secureApi;
