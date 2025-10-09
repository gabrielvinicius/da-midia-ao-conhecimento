// frontend/src/pages/LazyPages.tsx
/**
 * Definições de páginas lazy com code splitting otimizado
 */

import { createLazyComponent } from '../components/LazyWrapper';

// === Páginas de Autenticação ===
export const LoginPage = createLazyComponent(
  () => import('./LoginPage'),
  'LoginPage'
);

export const RegisterPage = createLazyComponent(
  () => import('./RegisterPage'),
  'RegisterPage'
);

// === Páginas de Mídia ===
export const DashboardPage = createLazyComponent(
  () => import('./DashboardPage'),
  'DashboardPage'
);

export const UploadPage = createLazyComponent(
  () => import('./UploadPage'),
  'UploadPage'
);

export const MediaDetailPage = createLazyComponent(
  () => import('./MediaDetailPage'),
  'MediaDetailPage'
);

// === Páginas Admin ===
export const AdminDashboardPage = createLazyComponent(
  () => import('../features/admin/pages/AdminDashboardPage'),
  'AdminDashboardPage'
);

export const AdminUsersPage = createLazyComponent(
  () => import('../features/admin/pages/AdminUsersPage'),
  'AdminUsersPage'
);

export const AdminAllMediaPage = createLazyComponent(
  () => import('../features/admin/pages/AdminAllMediaPage'),
  'AdminAllMediaPage'
);

// === Páginas de Configuração ===
export const SettingsPage = createLazyComponent(
  () => import('./SettingsPage'),
  'SettingsPage'
);

// === Páginas de Visualização ===
export const TranscriptionView = createLazyComponent(
  () => import('./TranscriptionView'),
  'TranscriptionView'
);

export const SummaryView = createLazyComponent(
  () => import('./SummaryView'),
  'SummaryView'
);

// === Página 404 ===
export const NotFoundPage = createLazyComponent(
  () => import('./NotFoundPage'),
  'NotFoundPage'
);

// === Preload Maps ===
// Mapa de preload baseado em rotas relacionadas
export const PRELOAD_MAP = {
  '/login': [
    () => import('./RegisterPage'),
    () => import('./DashboardPage')
  ],
  '/dashboard': [
    () => import('./UploadPage'),
    () => import('./MediaDetailPage')
  ],
  '/upload': [
    () => import('./MediaDetailPage'),
    () => import('../features/media/components/UploadForm')
  ],
  '/admin': [
    () => import('../features/admin/pages/AdminUsersPage'),
    () => import('../features/admin/pages/AdminAllMediaPage')
  ]
};