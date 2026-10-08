// Conta do usuário. A sessão (tokens e renovação) fica em services/auth.service.
import api from '@/lib/api';
import authService, { TokenResponse } from '@/services/auth.service';
import { User, UserCredentials, UserRegistration, ChangePasswordPayload } from '@/types';

/** O formulário do OAuth2 chama o e-mail de `username`. */
export const login = (credentials: UserCredentials): Promise<TokenResponse> =>
  authService.login({ username: credentials.email, password: credentials.password });

export type RegisterResult = User & { email_verification_required?: boolean };

export const register = async ({ email, password }: UserRegistration): Promise<RegisterResult> =>
  (await api.post<RegisterResult>('/auth/register', { email, password })).data;

export const getMe = async (): Promise<User> => (await api.get<User>('/auth/me')).data;

export const changePassword = async ({ old_password, new_password }: ChangePasswordPayload): Promise<void> => {
  await api.put('/auth/me/password', { old_password, new_password });
};

/** Se o servidor envia e-mails (confirmação do cadastro e nova senha). */
export const getAuthOptions = async (): Promise<{ email_enabled: boolean }> =>
  (await api.get<{ email_enabled: boolean }>('/auth/options')).data;

export const verifyEmail = async (token: string): Promise<void> => {
  await api.post('/auth/verify-email', { token });
};

export const resendVerification = async (email: string): Promise<void> => {
  await api.post('/auth/resend-verification', { email });
};

export const forgotPassword = async (email: string): Promise<void> => {
  await api.post('/auth/forgot-password', { email });
};

export const resetPassword = async (token: string, new_password: string): Promise<void> => {
  await api.post('/auth/reset-password', { token, new_password });
};
