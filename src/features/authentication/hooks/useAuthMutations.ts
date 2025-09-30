import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { login, register } from '../api';
import { useAuth } from '../../../contexts/AuthContext';
import { UserCredentials, UserRegistration } from '../../../types';

export const useLogin = () => {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: UserCredentials) => login(credentials),
    onSuccess: async (data) => {
      localStorage.setItem('token', data.access_token);
      // Manually refetch user data to update context
      const user = await queryClient.fetchQuery({ queryKey: ['currentUser'] });
      if (user) {
        setUser(user);
      }
      toast.success('Login successful!');
      navigate('/dashboard');
    },
    onError: (error) => {
      // The global error handler in `lib/api.ts` will already show a toast
      console.error('Login failed:', error);
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
