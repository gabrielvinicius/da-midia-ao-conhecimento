// frontend/src/components/LazyWrapper.tsx
/**
 * Wrapper para componentes lazy com loading states otimizados
 */

import React, { Suspense } from 'react';
import { LoadingSpinner } from './LoadingSpinner';

interface LazyWrapperProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  minLoadingTime?: number; // Tempo mínimo de loading para evitar flashing
}

// Cache de componentes carregados para evitar re-loading
const loadedComponents = new Set<string>();

export const LazyWrapper: React.FC<LazyWrapperProps> = ({ 
  children, 
  fallback,
  minLoadingTime = 300 
}) => {
  const [isMinTimePassed, setIsMinTimePassed] = React.useState(false);
  
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setIsMinTimePassed(true);
    }, minLoadingTime);
    
    return () => clearTimeout(timer);
  }, [minLoadingTime]);

  const defaultFallback = (
    <div className="flex items-center justify-center min-h-[200px]">
      <div className="text-center">
        <LoadingSpinner size={12} />
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Carregando componente...
        </p>
      </div>
    </div>
  );

  return (
    <Suspense fallback={fallback || defaultFallback}>
      {children}
    </Suspense>
  );
};

// HOC para criar componentes lazy com wrapper automático
export function createLazyComponent<T = any>(
  importFn: () => Promise<{ default: React.ComponentType<T> }>,
  componentName?: string
) {
  const LazyComponent = React.lazy(async () => {
    const start = performance.now();
    
    try {
      const module = await importFn();
      const loadTime = performance.now() - start;
      
      // Marcar como carregado
      if (componentName) {
        loadedComponents.add(componentName);
      }
      
      return module;
    } catch (error) {
      console.error(`❌ Failed to load ${componentName || 'component'}:`, error);
      throw error;
    }
  });

  // Adicionar displayName para debugging
  (LazyComponent as any).displayName = `Lazy(${componentName || 'Component'})`;

  return LazyComponent;
}

// Hook para preload de componentes
export function usePreloadComponent(
  importFn: () => Promise<{ default: React.ComponentType<any> }>,
  condition: boolean = true
) {
  React.useEffect(() => {
    if (condition) {
      // Preload silencioso
      importFn().catch(() => {
        // Ignorar erros de preload
      });
    }
  }, [importFn, condition]);
}

// Componente para preload baseado em hover
interface PreloadOnHoverProps {
  importFn: () => Promise<{ default: React.ComponentType<any> }>;
  children: React.ReactNode;
  delay?: number;
}

export const PreloadOnHover: React.FC<PreloadOnHoverProps> = ({
  importFn,
  children,
  delay = 100
}) => {
  const [isPreloaded, setIsPreloaded] = React.useState(false);

  const handleMouseEnter = React.useCallback(() => {
    if (!isPreloaded) {
      setTimeout(() => {
        importFn()
          .then(() => setIsPreloaded(true))
          .catch(() => {});
      }, delay);
    }
  }, [importFn, isPreloaded, delay]);

  return (
    <div onMouseEnter={handleMouseEnter}>
      {children}
    </div>
  );
};

// Componente para lazy loading com intersection observer
interface LazyOnViewProps {
  importFn: () => Promise<{ default: React.ComponentType<any> }>;
  fallback?: React.ReactNode;
  rootMargin?: string;
  threshold?: number;
  children: React.ReactNode;
}

export const LazyOnView: React.FC<LazyOnViewProps> = ({
  importFn,
  fallback,
  rootMargin = '50px',
  threshold = 0.1,
  children
}) => {
  const [isVisible, setIsVisible] = React.useState(false);
  const [isLoaded, setIsLoaded] = React.useState(false);
  const elementRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isLoaded) {
          setIsVisible(true);
          importFn()
            .then(() => setIsLoaded(true))
            .catch(() => {});
        }
      },
      { rootMargin, threshold }
    );

    if (elementRef.current) {
      observer.observe(elementRef.current);
    }

    return () => observer.disconnect();
  }, [importFn, isLoaded, rootMargin, threshold]);

  return (
    <div ref={elementRef}>
      {isVisible ? children : (fallback || <div>Loading...</div>)}
    </div>
  );
};
