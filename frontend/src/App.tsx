import { Suspense, lazy } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { WebSocketProvider } from "./contexts/WebSocketContext";

import AppLayout from "./components/AppLayout";
import AdminLayout from "./components/AdminLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import { Loader2 } from "lucide-react";

// Cada página é carregada só quando visitada.
const LoginPage = lazy(() => import("./pages/LoginPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const MediaDetailPage = lazy(() => import("./pages/MediaDetailPage"));
const UploadPage = lazy(() => import("./pages/UploadPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const SearchPage = lazy(() => import("./pages/SearchPage"));
// Conta: confirmação de e-mail e nova senha (links enviados por e-mail).
const CheckEmailPage = lazy(() => import("./pages/AccountPages").then((m) => ({ default: m.CheckEmailPage })));
const ConfirmEmailPage = lazy(() => import("./pages/AccountPages").then((m) => ({ default: m.ConfirmEmailPage })));
const ForgotPasswordPage = lazy(() => import("./pages/AccountPages").then((m) => ({ default: m.ForgotPasswordPage })));
const ResetPasswordPage = lazy(() => import("./pages/AccountPages").then((m) => ({ default: m.ResetPasswordPage })));

// As páginas do administrador têm exportação nomeada; lazy() pede a padrão.
const AdminDashboardPage = lazy(() => import("./features/admin/pages/AdminDashboardPage").then(module => ({ default: module.AdminDashboardPage })));
const AdminAnalyticsPage = lazy(() => import("./features/admin/pages/AdminAnalyticsPage").then(module => ({ default: module.AdminAnalyticsPage })));
const AdminUsersPage = lazy(() => import("./features/admin/pages/AdminUsersPage").then(module => ({ default: module.AdminUsersPage })));
const AdminQueuePage = lazy(() => import("./features/admin/pages/AdminQueuePage").then(module => ({ default: module.AdminQueuePage })));
const AdminAllMediaPage = lazy(() => import("./features/admin/pages/AdminAllMediaPage").then(module => ({ default: module.AdminAllMediaPage })));

const PageLoader = () => (
  <div className="flex h-screen w-full items-center justify-center bg-gray-50 dark:bg-gray-900">
    <Loader2 className="h-10 w-10 animate-spin text-primary" />
  </div>
);

const App = () => {
  return (
    <AuthProvider>
      <WebSocketProvider>
        <Router>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* Públicas */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/confirme-seu-email" element={<CheckEmailPage />} />
              <Route path="/confirmar-email" element={<ConfirmEmailPage />} />
              <Route path="/esqueci-a-senha" element={<ForgotPasswordPage />} />
              <Route path="/redefinir-senha" element={<ResetPasswordPage />} />

              {/* Usuário logado */}
              <Route element={<ProtectedRoute />}>
                <Route path="/" element={<AppLayout />}>
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="dashboard" element={<DashboardPage />} />
                  <Route path="upload" element={<UploadPage />} />
                  <Route path="search" element={<SearchPage />} />
                  <Route path="media/:id" element={<MediaDetailPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                </Route>
              </Route>

              {/* Administrador */}
              <Route element={<AdminRoute />}>
                <Route path="/admin" element={<AdminLayout />}>
                  <Route index element={<Navigate to="/admin/dashboard" replace />} />
                  <Route path="dashboard" element={<AdminDashboardPage />} />
                  <Route path="analytics" element={<AdminAnalyticsPage />} />
                  <Route path="users" element={<AdminUsersPage />} />
                  <Route path="media" element={<AdminAllMediaPage />} />
                  <Route path="queue" element={<AdminQueuePage />} />
                </Route>
              </Route>

              {/* Endereço inexistente: antes mandava para o login até quem estava logado. */}
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </Router>
      </WebSocketProvider>
    </AuthProvider>
  );
};

export default App;
