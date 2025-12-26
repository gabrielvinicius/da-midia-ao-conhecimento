import authService, { LoginData, RegisterData, ChangePasswordData } from '@/services/auth.service';
import { User, UserCredentials, UserRegistration, ChangePasswordPayload } from '@/types';

export interface LoginResponse {
  message: string;
  access_token?: string;
  token_type?: string;
}

export const login = async (credentials: UserCredentials): Promise<LoginResponse> => {
  try {
    const loginData: LoginData = {
      username: credentials.email,
      password: credentials.password,
    };
    
    const response = await authService.login(loginData);
    return response;
  } catch (error) {
    console.error('❌ Erro no login:', error);
    throw error;
  }
};

export const register = async (userData: UserRegistration): Promise<User> => {
  const registerData: RegisterData = {
    email: userData.email,
    password: userData.password,
  };
  
  const response = await authService.register(registerData);
  return response;
};

export const getMe = async (): Promise<User> => {
  const response = await authService.getCurrentUser();
  return response;
};

export const changePassword = async (payload: ChangePasswordPayload): Promise<void> => {
  const changeData: ChangePasswordData = {
    old_password: payload.old_password,
    new_password: payload.new_password,
  };
  
  await authService.changePassword(changeData);
};
