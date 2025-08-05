// src/hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { User } from '../types';

export const useAuth = () => {
    const queryClient = useQueryClient();
    const navigate = useNavigate();

    // Query: Carregar usuário autenticado
    const {
        data: user,
        isLoading,
        error,
        refetch,
    } = useQuery<User | null>({
        queryKey: ['auth'],
        queryFn: async () => {
            try {
                const res = await api.get('/auth/me');
                return res.data;
            } catch (err) {
                return null;
            }
        },
        retry: false,
        refetchOnWindowFocus: false,
    });

    // Mutation: Login
    const loginMutation = useMutation({
        mutationFn: async ({ email, password }: { email: string; password: string }) => {
            const res = await api.post('/auth/login', { email, password });
            return res.data;
        },
        onSuccess: (data) => {
            localStorage.setItem('token', data.access_token);
            queryClient.setQueryData(['auth'], data.user);
            navigate('/user');
        },
    });

    // Mutation: Registro
    const registerMutation = useMutation({
        mutationFn: async ({ email, password }: { email: string; password: string }) => {
            const res = await api.post('/auth/register', { email, password });
            return res.data;
        },
        onSuccess: () => {
            navigate('/login');
        },
    });

    // Logout (não é mutation, é ação direta)
    const logout = () => {
        localStorage.removeItem('token');
        queryClient.setQueryData(['auth'], null);
        queryClient.removeQueries();
        navigate('/login');
    };

    return {
        user,
        isAuthenticated: !!user,
        loading: isLoading,
        login: loginMutation.mutate,
        register: registerMutation.mutate,
        logout,
        isLoggingIn: loginMutation.isPending,
        isRegistering: registerMutation.isPending,
    };
};