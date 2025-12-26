// src/services/auth.service.ts
import api, { getApiBaseUrl } from "@/lib/api";
import { User, UserRole } from "@/types";

export interface LoginData {
    username: string;
    password: string;
}

export interface RegisterData {
    email: string;
    password: string;
}

export interface TokenResponse {
    message: string;
    access_token: string;
    token_type: string;
}

export interface ChangePasswordData {
    old_password: string;
    new_password: string;
}

class AuthService {
    private static instance: AuthService;
    private refreshPromise: Promise<void> | null = null;
    private isRefreshing = false;
    private hasActiveSession: boolean;

    private constructor() {
        this.hasActiveSession = sessionStorage.getItem('has_session') === 'true';
    }

    public static getInstance(): AuthService {
        if (!AuthService.instance) {
            AuthService.instance = new AuthService();
        }
        return AuthService.instance;
    }

    /**
     * Login usando cookies httpOnly entregues pelo backend FastAPI
     */
    async login(data: LoginData): Promise<TokenResponse> {
        const payload = new URLSearchParams();
        payload.append('username', data.username);
        payload.append('password', data.password);

        const response = await api.post<TokenResponse>("/auth/token", payload, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            withCredentials: true, // necessário para receber refresh cookie
        });

        this.hasActiveSession = true;
        sessionStorage.setItem('has_session', 'true');
        if (response.data?.access_token) {
            sessionStorage.setItem('access_token', response.data.access_token);
        }

        return response.data;
    }

    /**
     * Registrar novo usuário
     */
    async register(data: RegisterData): Promise<User> {
        // Backend returns UserResponse, which matches our User type
        const response = await api.post<User>("/auth/register", data);
        return response.data;
    }

    /**
     * Buscar dados do usuário atual
     */
    async getCurrentUser(): Promise<User> {
        const response = await api.get<User>("/auth/me");
        this.hasActiveSession = true;
        sessionStorage.setItem('has_session', 'true');
        return response.data;
    }

    /**
     * Refresh token (apenas para modo seguro)
     */
    async refreshToken(): Promise<TokenResponse> {
        const url = `${getApiBaseUrl()}/auth/refresh`;
        const response = await api.post<TokenResponse>(
            url,
            {},
            { withCredentials: true }
        );
        if (response.data?.access_token) {
            sessionStorage.setItem('access_token', response.data.access_token);
            sessionStorage.setItem('has_session', 'true');
            this.hasActiveSession = true;
        }
        return response.data;
    }

    private async _performRefresh(): Promise<void> {
        await this.refreshToken();
    }

    /**
     * Logout
     */
    async logout(): Promise<void> {
        try {
            // Remove refresh cookie
            await api.post("/auth/logout", {}, { withCredentials: true });
        } catch (error) {
            console.warn('Logout no servidor falhou:', error);
        } finally {
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
        sessionStorage.removeItem('csrf_token');
        sessionStorage.removeItem('has_session');
        sessionStorage.removeItem('access_token');
        this.hasActiveSession = false;
    }

    /**
     * Verificar se o usuário está autenticado
     */
    isAuthenticated(): boolean {
        return this.hasActiveSession;
    }

    /**
     * Obter token atual
     */
    getToken(): string | null {
        return sessionStorage.getItem('access_token');
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
export const login = (data: LoginData) => authService.login(data);
export const loginSecure = (data: LoginData) => authService.login(data);
export const register = (data: RegisterData) => authService.register(data);
export const getCurrentUser = () => authService.getCurrentUser();
export const logout = () => authService.logout();
export const changePassword = (data: ChangePasswordData) => authService.changePassword(data);
