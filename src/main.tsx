// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ErrorBoundary } from 'react-error-boundary';
import App from './App';

// Verifica se o elemento root existe
const container = document.getElementById('root');
if (!container) {
    throw new Error('Elemento root não encontrado');
}

// Configuração do QueryClient com tratamento de erros
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000 * 60 * 5, // 5 minutos
            //cacheTime: 1000 * 60 * 30, // 30 minutos
            retry: (failureCount, error) => {
                // Não tentar novamente para erros 404
                if ((error as any)?.response?.status === 404) {
                    return false;
                }
                // Tentar até 2 vezes no total (original + 1 retry)
                return failureCount < 1;
            },
            retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
            refetchOnWindowFocus: false
        }
    }
});

// Componente de fallback para erros globais
function ErrorFallback({ error, resetErrorBoundary }: {
    error: Error;
    resetErrorBoundary: () => void
}) {
    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4">
            <h1 className="text-2xl font-bold text-red-600 mb-4">Erro inesperado</h1>
            <p className="text-gray-700 mb-6 max-w-md text-center">
                {error.message || 'Ocorreu um erro ao carregar a aplicação'}
            </p>
            <button
                onClick={resetErrorBoundary}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
                Tentar novamente
            </button>
        </div>
    );
}

ReactDOM.createRoot(container).render(
    <React.StrictMode>
        <QueryClientProvider client={queryClient}>
            <ErrorBoundary
                FallbackComponent={ErrorFallback}
                onReset={() => window.location.reload()}
            >
                <App />
            </ErrorBoundary>
            <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
    </React.StrictMode>
);