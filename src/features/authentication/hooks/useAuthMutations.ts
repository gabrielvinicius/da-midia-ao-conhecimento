import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { login, register, changePassword } from '../api';
import { useAuth } from '@/contexts/AuthContext';
import { UserCredentials, UserRegistration, ChangePasswordPayload } from '@/types';

export const useLogin = () => {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: UserCredentials) => login(credentials),
    onSuccess: async (data) => {
      localStorage.setItem('token', data.access_token);
      const user = await queryClient.fetchQuery({ queryKey: ['currentUser'] });
      if (user) {
        setUser(user);
      }
      toast.success('Login successful!');
      navigate('/dashboard');
    },
    onError: (error) => {
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

export const useChangePassword = () => {
  const { logout } = useAuth();

  return useMutation({
    mutationFn: (payload: ChangePasswordPayload) => changePassword(payload),
    onSuccess: () => {
      toast.success('Password changed successfully. Please log in again.');
      // For security, log the user out after a password change.
      logout();
    },
    onError: (error) => {
      console.error('Failed to change password:', error);
    },
  });
};
