import api from "@/lib/api";
import { User, UserCredentials, UserRegistration, ChangePasswordPayload } from "@/types";

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export const login = async (credentials: UserCredentials): Promise<LoginResponse> => {
  console.log('Tentando login com:', { email: credentials.email });
  
  try {
    // Primeiro tenta o endpoint legacy que retorna token no body
    const response = await api.post<LoginResponse>("/auth/token/legacy", {
      username: credentials.email, // The backend expects 'username'
      password: credentials.password,
    });
    
    console.log('Login response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Erro no login:', error);
    throw error;
  }
};

export const register = async (userData: UserRegistration): Promise<User> => {
  const response = await api.post<User>("/auth/register", userData);
  return response.data;
};

export const getMe = async (): Promise<User> => {
  const response = await api.get<User>("/auth/me");
  return response.data;
};

export const changePassword = async (payload: ChangePasswordPayload): Promise<void> => {
  await api.put("/auth/me/password", payload);
};
