import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { User } from '../types';
import authService from '../services/auth.service';

// Define the shape of the context value
interface AuthContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

// Create the context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Function to fetch the current user
const fetchCurrentUser = async (): Promise<User | null> => {
  try {
    console.log('👤 Buscando dados do usuário atual...');
    const user = await authService.getCurrentUser();
    console.log('✅ Dados do usuário obtidos via AuthService:', user);
    return user;
  } catch (error) {
    console.error('❌ Erro ao buscar usuário:', error);
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
      console.log('✅ Usuário definido no contexto:', currentUser);
    }
  }, [currentUser]);

  const logout = async () => {
    console.log('🚪 Fazendo logout...');
    try {
      await authService.logout();
    } catch (error) {
      console.warn('Erro no logout:', error);
    } finally {
      setUser(null);
      queryClient.clear(); // Clear all query cache on logout
      console.log('✅ Logout concluído');
      window.location.href = '/login';
    }
  };

  const refreshToken = async () => {
    console.log('🔄 Refresh token solicitado pelo contexto...');
    try {
      await authService.refreshToken();
      // Invalidar query para buscar dados atualizados
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
    } catch (error) {
      console.error('❌ Erro no refresh token:', error);
      throw error;
    }
  };

  const value = {
    user,
    setUser,
    isAuthenticated: !!user,
    isLoading,
    logout,
    refreshToken,
  };

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

// Export useAuthContext as alias for backward compatibility
export const useAuthContext = useAuth;
