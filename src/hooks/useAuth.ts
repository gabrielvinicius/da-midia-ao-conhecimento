// src/hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { login, register } from '../services/auth.service'; // ← Import dos serviços
import { User } from '../types';

export const useAuth = () => {
    const queryClient = useQueryClient();
    const navigate = useNavigate();

    // Query: Carregar usuário autenticado
    const {
        data: user,
        isLoading,
        error,
    } = useQuery<User | null>({
        queryKey: ['auth'],
        queryFn: async () => {
            try {
                const res = await fetch('/auth/me', {
                    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
                });
                if (!res.ok) throw new Error();
                return await res.json();
            } catch (err) {
                return null;
            }
        },
        retry: false,
        refetchOnWindowFocus: false,
    });

    // Mutation: Login
    const loginMutation = useMutation({
        mutationFn: login, // ← Usa o serviço
        onSuccess: (data) => {
            localStorage.setItem('token', data.access_token);
            queryClient.setQueryData(['auth'], data.user);
            navigate('/user');
        },
    });

    // Mutation: Registro
    const registerMutation = useMutation({
        mutationFn: register, // ← Usa o serviço
        onSuccess: () => {
            navigate('/login');
        },
    });

    // Logout
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