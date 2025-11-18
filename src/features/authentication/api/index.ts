import authService, { LoginData, RegisterData, ChangePasswordData } from '@/services/auth.service';
import { User, UserCredentials, UserRegistration, ChangePasswordPayload } from '@/types';

export interface LoginResponse {
  message: string;
}

export const login = async (credentials: UserCredentials): Promise<LoginResponse> => {
  console.log('🔐 Fazendo login via AuthService:', { email: credentials.email });
  
  try {
    const loginData: LoginData = {
      username: credentials.email,
      password: credentials.password,
    };
    
    const response = await authService.login(loginData);
    
    console.log('✅ Login bem-sucedido:', response);
    return response;
  } catch (error) {
    console.error('❌ Erro no login:', error);
    throw error;
  }
};

export const register = async (userData: UserRegistration): Promise<User> => {
  console.log('📝 Registrando usuário via AuthService:', { email: userData.email });
  
  const registerData: RegisterData = {
    email: userData.email,
    password: userData.password,
  };
  
  const response = await authService.register(registerData);
  console.log('✅ Registro bem-sucedido:', response);
  return response;
};

export const getMe = async (): Promise<User> => {
  console.log('👤 Buscando dados do usuário via AuthService');
  const response = await authService.getCurrentUser();
  console.log('✅ Dados do usuário obtidos:', response);
  return response;
};

export const changePassword = async (payload: ChangePasswordPayload): Promise<void> => {
  console.log('🔒 Alterando senha via AuthService');
  
  const changeData: ChangePasswordData = {
    old_password: payload.old_password,
    new_password: payload.new_password,
  };
  
  await authService.changePassword(changeData);
  console.log('✅ Senha alterada com sucesso');
};
