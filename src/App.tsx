import { Suspense, lazy } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { WebSocketProvider } from "./contexts/WebSocketContext";

// Layouts
import AppLayout from "./components/AppLayout";
import AdminLayout from "./components/AdminLayout";

// Route Protectors
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";

// Components
import { Loader2 } from "lucide-react";

// Lazy Load Pages for Code Splitting
const LoginPage = lazy(() => import("./pages/LoginPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));

// User-facing Pages
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const MediaDetailPage = lazy(() => import("./pages/MediaDetailPage"));
const UploadPage = lazy(() => import("./pages/UploadPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const SearchPage = lazy(() => import("./pages/SearchPage"));

// Admin Pages
// Note: These need to be exported as default or named exports correctly in their files.
// Assuming named exports for features based on previous file content, we use module destructuring pattern if needed,
// but React.lazy expects a default export.
// If features/admin/pages exports named components, we adapt:
const AdminDashboardPage = lazy(() => import("./features/admin/pages/AdminDashboardPage").then(module => ({ default: module.AdminDashboardPage })));
const AdminAnalyticsPage = lazy(() => import("./features/admin/pages/AdminAnalyticsPage").then(module => ({ default: module.AdminAnalyticsPage })));
const AdminUsersPage = lazy(() => import("./features/admin/pages/AdminUsersPage").then(module => ({ default: module.AdminUsersPage })));
const AdminAllMediaPage = lazy(() => import("./features/admin/pages/AdminAllMediaPage").then(module => ({ default: module.AdminAllMediaPage })));

// Loading Fallback
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
              {/* Public routes */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />

              {/* Main application routes for standard users */}
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

              {/* Admin routes */}
              <Route element={<AdminRoute />}>
                <Route path="/admin" element={<AdminLayout />}>
                  <Route index element={<Navigate to="/admin/dashboard" replace />} />
                  <Route path="dashboard" element={<AdminDashboardPage />} />
                  <Route path="analytics" element={<AdminAnalyticsPage />} />
                  <Route path="users" element={<AdminUsersPage />} />
                  <Route path="media" element={<AdminAllMediaPage />} />
                </Route>
              </Route>

              {/* Fallback for any other route */}
              <Route path="*" element={<Navigate to="/login" />} />
            </Routes>
          </Suspense>
        </Router>
      </WebSocketProvider>
    </AuthProvider>
  );
};

export default App;
