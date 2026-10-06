// Conta do usuário. A sessão (tokens e renovação) fica em services/auth.service.
import api from '@/lib/api';
import authService, { TokenResponse } from '@/services/auth.service';
import { User, UserCredentials, UserRegistration, ChangePasswordPayload } from '@/types';

/** O formulário do OAuth2 chama o e-mail de `username`. */
export const login = (credentials: UserCredentials): Promise<TokenResponse> =>
  authService.login({ username: credentials.email, password: credentials.password });

export const register = async ({ email, password }: UserRegistration): Promise<User> =>
  (await api.post<User>('/auth/register', { email, password })).data;

export const getMe = async (): Promise<User> => (await api.get<User>('/auth/me')).data;

export const changePassword = async ({ old_password, new_password }: ChangePasswordPayload): Promise<void> => {
  await api.put('/auth/me/password', { old_password, new_password });
};
