// src/contexts/AuthContext.tsx
import { createContext, useContext, ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';

const AuthContext = createContext<ReturnType<typeof useAuth> | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const auth = useAuth();
    return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
    const context = useContext(AuthContext);
    if (!context) throw new Error('useAuthContext deve estar dentro de AuthProvider');
    return context;
}