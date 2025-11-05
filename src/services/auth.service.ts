// src/services/auth.service.ts
import api from "../lib/api";

export interface LoginData {
    username: string;
    password: string;
}

export interface RegisterData {
    email: string;
    password: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    csrf_token?: string;
}

import { UserRole } from "../types";

export interface User {
    id: string;
    email: string;
    role: UserRole;
    csrf_token?: string;
}

export interface ChangePasswordData {
    old_password: string;
    new_password: string;
}

class AuthService {
    private static instance: AuthService;
    private refreshPromise: Promise<void> | null = null;
    private isRefreshing = false;

    public static getInstance(): AuthService {
        if (!AuthService.instance) {
            AuthService.instance = new AuthService();
        }
        return AuthService.instance;
    }

    /**
     * Login com token no localStorage (legacy mode)
     */
    async loginLegacy(data: LoginData): Promise<TokenResponse> {
        console.log('🔐 Login Legacy - usando localStorage');
        const response = await api.post<TokenResponse>("/auth/token/legacy", {
            username: data.username,
            password: data.password
        });
        
        // Armazenar token no localStorage
        if (response.data.access_token) {
            localStorage.setItem('token', response.data.access_token);
            console.log('✅ Token armazenado no localStorage');
        }
        
        return response.data;
    }

    /**
     * Login seguro com cookies httpOnly
     */
    async loginSecure(data: LoginData): Promise<TokenResponse> {
        console.log('🛡️ Login Seguro - usando cookies httpOnly');
        const response = await api.post<TokenResponse>("/auth/token", {
            username: data.username,
            password: data.password
        }, {
            withCredentials: true // Importante para cookies
        });
        
        // Com login seguro, o token vai para cookies httpOnly
        // Só salvamos o CSRF token se necessário
        if (response.data.csrf_token) {
            sessionStorage.setItem('csrf_token', response.data.csrf_token);
            console.log('✅ CSRF token armazenado');
        }
        
        return response.data;
    }

    /**
     * Registrar novo usuário
     */
    async register(data: RegisterData): Promise<User> {
        const response = await api.post<User>("/auth/register", data);
        return response.data;
    }

    /**
     * Buscar dados do usuário atual
     */
    async getCurrentUser(): Promise<User> {
        const response = await api.get<User>("/auth/me");
        return response.data;
    }

    /**
     * Refresh token (apenas para modo seguro)
     */
    async refreshToken(): Promise<TokenResponse> {
        if (this.isRefreshing && this.refreshPromise) {
            await this.refreshPromise;
            return { access_token: 'refreshed', token_type: 'bearer' };
        }

        this.isRefreshing = true;
        this.refreshPromise = this._performRefresh();

        try {
            const result = await this.refreshPromise;
            return { access_token: 'refreshed', token_type: 'bearer' };
        } finally {
            this.isRefreshing = false;
            this.refreshPromise = null;
        }
    }

    private async _performRefresh(): Promise<void> {
        console.log('🔄 Refreshing token...');
        const response = await api.post<TokenResponse>("/auth/refresh", {}, {
            withCredentials: true
        });
        
        if (response.data.csrf_token) {
            sessionStorage.setItem('csrf_token', response.data.csrf_token);
            console.log('✅ Token refreshed successfully');
        }
    }

    /**
     * Logout
     */
    async logout(): Promise<void> {
        try {
            // Tentar logout no servidor (para cookies)
            await api.post("/auth/logout", {}, {
                withCredentials: true
            });
        } catch (error) {
            console.warn('Logout no servidor falhou:', error);
        } finally {
            // Limpar dados locais sempre
            this.clearLocalAuth();
        }
    }

    /**
     * Alterar senha
     */
    async changePassword(data: ChangePasswordData): Promise<void> {
        await api.put("/auth/me/password", data);
    }

    /**
     * Limpar dados de autenticação local
     */
    clearLocalAuth(): void {
        localStorage.removeItem('token');
        sessionStorage.removeItem('csrf_token');
        console.log('🧹 Dados de autenticação limpos');
    }

    /**
     * Verificar se o usuário está autenticado
     */
    isAuthenticated(): boolean {
        const token = localStorage.getItem('token');
        // TODO: Verificar se o token não está expirado
        return !!token;
    }

    /**
     * Obter token atual
     */
    getToken(): string | null {
        return localStorage.getItem('token');
    }

    /**
     * Obter CSRF token
     */
    getCsrfToken(): string | null {
        return sessionStorage.getItem('csrf_token');
    }
}

// Exportar instância singleton
const authService = AuthService.getInstance();
export default authService;

// Exportar métodos individuais para compatibilidade
export const login = (data: LoginData) => authService.loginLegacy(data);
export const loginSecure = (data: LoginData) => authService.loginSecure(data);
export const register = (data: RegisterData) => authService.register(data);
export const getCurrentUser = () => authService.getCurrentUser();
export const logout = () => authService.logout();
export const changePassword = (data: ChangePasswordData) => authService.changePassword(data);