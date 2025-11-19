import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { WebSocketProvider } from "./contexts/WebSocketContext";
import { ProvidersProvider } from "./features/providers/context/ProvidersContext";

// Layouts
import AppLayout from "./components/AppLayout";
import AdminLayout from "./components/AdminLayout";

// Route Protectors
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";

// Public Pages
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

// User-facing Pages
import DashboardPage from "./pages/DashboardPage";
import MediaDetailPage from "./pages/MediaDetailPage";
import UploadPage from "./pages/UploadPage";
import SettingsPage from "./pages/SettingsPage"; // Import the new page
import { AdminAnalyticsPage } from "./features/admin/pages/AdminAnalyticsPage";

// Admin Pages
import { AdminDashboardPage } from "./features/admin/pages/AdminDashboardPage";
import { AdminUsersPage } from "./features/admin/pages/AdminUsersPage";
import { AdminAllMediaPage } from "./features/admin/pages/AdminAllMediaPage";

const App = () => {
  return (
    <AuthProvider>
      <WebSocketProvider>
        <ProvidersProvider>
          <Router>
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
                <Route path="media/:id" element={<MediaDetailPage />} />
                <Route path="settings" element={<SettingsPage />} /> {/* Add the new route */}
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
        </Router>
        </ProvidersProvider>
      </WebSocketProvider>
    </AuthProvider>
  );
};

export default App;
