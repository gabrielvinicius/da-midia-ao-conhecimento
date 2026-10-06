import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { login, register, changePassword, getMe } from '../api';
import { useAuth } from '@/contexts/AuthContext';
import { apiErrorMessage } from '@/lib/errors';
import { UserCredentials, UserRegistration, ChangePasswordPayload } from '@/types';

export const useLogin = () => {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: UserCredentials) => login(credentials),
    onSuccess: async () => {
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
    onError: (error) => {
      toast.error(apiErrorMessage(error, 'Não foi possível entrar. Tente novamente.'));
    },
  });
};

export const useRegister = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (userData: UserRegistration) => register(userData),
    onSuccess: () => {
      toast.success('Cadastro realizado. Entre com o seu e-mail e senha.');
      navigate('/login');
    },
    onError: (error) => {
      // 409: e-mail já cadastrado; 400/422: dados inválidos.
      toast.error(apiErrorMessage(error, 'Não foi possível concluir o cadastro.'));
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
      toast.error(apiErrorMessage(error, 'Não foi possível alterar a senha.'));
    },
  });
};
