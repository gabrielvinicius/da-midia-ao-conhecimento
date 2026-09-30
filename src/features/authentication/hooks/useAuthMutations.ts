import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { login, register, changePassword, getMe } from '../api';
import { useAuth } from '@/contexts/AuthContext';
import { UserCredentials, UserRegistration, ChangePasswordPayload } from '@/types';

export const useLogin = () => {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: UserCredentials) => login(credentials),
    onSuccess: async (data) => {
      try {
        // Buscar dados do usuário
        const user = await getMe();
        // Atualizar contexto e cache
        setUser(user);
        queryClient.setQueryData(['currentUser'], user);
        
        toast.success('Login realizado com sucesso!');
        navigate('/dashboard');
      } catch (userError) {
        console.error('Erro ao buscar dados do usuário:', userError);
        toast.error('Erro ao carregar dados do usuário');
      }
    },
    onError: (error: any) => {
      console.error('Login failed:', error);
      const message = error?.response?.data?.detail || error?.message || 'Credenciais inválidas';
      toast.error(message);
    },
  });
};

export const useRegister = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (userData: UserRegistration) => register(userData),
    onSuccess: () => {
      toast.success('Registration successful! Please log in.');
      navigate('/login');
    },
    onError: (error) => {
      console.error('Registration failed:', error);
    },
  });
};

export const useChangePassword = () => {
  const { logout } = useAuth();

  return useMutation({
    mutationFn: (payload: ChangePasswordPayload) => changePassword(payload),
    onSuccess: () => {
      toast.success('Senha alterada. Entre novamente com a nova senha.');
      // For security, log the user out after a password change.
      logout();
    },
    onError: (error) => {
      console.error('Failed to change password:', error);
    },
  });
};
