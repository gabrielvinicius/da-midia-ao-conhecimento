// Sessão do usuário: único dono do token de acesso e da renovação.
import api, { bindSession } from "@/lib/api";

export interface LoginData {
    username: string;
    password: string;
}

export interface TokenResponse {
    message: string;
    access_token: string;
    token_type: string;
}

const ACCESS_TOKEN_KEY = "access_token";

class AuthService {
    private refreshing: Promise<boolean> | null = null;

    /** Token de acesso da aba (vai só no cabeçalho Authorization). */
    getToken(): string | null {
        return sessionStorage.getItem(ACCESS_TOKEN_KEY);
    }

    hasSession(): boolean {
        return this.getToken() !== null;
    }

    async login(data: LoginData): Promise<TokenResponse> {
        const payload = new URLSearchParams();
        payload.append("username", data.username);
        payload.append("password", data.password);
        const response = await api.post<TokenResponse>("/auth/token", payload, {
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            withCredentials: true, // recebe o cookie de renovação
        });
        this.storeToken(response.data?.access_token);
        return response.data;
    }

    /**
     * Renova a sessão pelo cookie, uma vez só para todos os pedidos.
     *
     * Quando o token de acesso expira, várias requisições recebem 401 ao mesmo
     * tempo. Antes, cada uma pedia a sua renovação; como o token de renovação
     * só vale uma vez, todas menos a primeira falhavam e a sessão era apagada
     * a cada 30 minutos. Agora as que chegam durante a renovação esperam por ela.
     */
    refreshSession(): Promise<boolean> {
        if (!this.refreshing) {
            this.refreshing = api
                .post<TokenResponse>("/auth/refresh", {}, { withCredentials: true })
                .then((response) => {
                    this.storeToken(response.data?.access_token);
                    return this.hasSession();
                })
                .catch(() => false)
                .finally(() => {
                    this.refreshing = null;
                });
        }
        return this.refreshing;
    }

    /**
     * Ao abrir a aplicação: usa o token da aba ou, numa aba nova, tenta renovar
     * pelo cookie. Sem sessão (visitante), devolve false sem nenhum aviso.
     */
    async restoreSession(): Promise<boolean> {
        return this.hasSession() || this.refreshSession();
    }

    async logout(): Promise<void> {
        try {
            await api.post("/auth/logout", {}, { withCredentials: true }); // revoga a renovação
        } catch (error) {
            console.warn("Logout no servidor falhou:", error);
        } finally {
            this.clearLocalAuth();
        }
    }

    clearLocalAuth(): void {
        sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    }

    private storeToken(token: string | undefined): void {
        if (token) sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
    }
}

const authService = new AuthService();
bindSession(authService);
export default authService;
