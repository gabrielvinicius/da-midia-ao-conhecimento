import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { User } from '../types';
import authService from '../services/auth.service';
import { getMe } from '@/features/authentication/api';

// Define the shape of the context value
interface AuthContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  logout: () => void;
}

// Create the context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Usuário da sessão, ou null para um visitante. Numa aba nova, a sessão é
 * recuperada pelo cookie de renovação; sem ela, nada é pedido à API (antes,
 * o 401 de /auth/me mostrava "Sessão expirada" na tela de login).
 */
const fetchCurrentUser = async (): Promise<User | null> => {
  if (!(await authService.restoreSession())) return null;
  try {
    return await getMe();
  } catch {
    authService.clearLocalAuth();
    return null;
  }
};

// Create the provider component
export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const queryClient = useQueryClient();

  const { data: currentUser, isLoading } = useQuery({
    queryKey: ['currentUser'],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false, // Don't retry on failure, as it means user is not logged in
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (currentUser) {
      setUser(currentUser);
    }
  }, [currentUser]);

  const logout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.warn('Erro no logout:', error);
    } finally {
      setUser(null);
      queryClient.clear(); // Clear all query cache on logout
      const logoutEvent = new CustomEvent('app:logout');
      window.dispatchEvent(logoutEvent);
    }
  };

  // O usuário vindo da consulta vale já na mesma renderização em que ela
  // termina; o useEffect acima só copia para o estado depois. Sem isso, ao
  // recarregar a página, a rota protegida via isLoading=false e user=null por
  // um instante e mandava para o login.
  const effectiveUser = user ?? currentUser ?? null;

  const value = {
    user: effectiveUser,
    setUser,
    isAuthenticated: !!effectiveUser,
    isLoading,
    logout,
  };

  useEffect(() => {
    const handler = () => {
      setUser(null);
      queryClient.clear();
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    };
    window.addEventListener('app:logout', handler);
    return () => window.removeEventListener('app:logout', handler);
  }, [queryClient]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use the auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

