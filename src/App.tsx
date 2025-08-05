// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from "./contexts/AuthContext";
import { DarkModeProvider } from "./contexts/DarkModeContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import UserDashboard from "./pages/UserDashboard";
import SummaryView from "./pages/SummaryView";
import TranscriptionView from "./pages/TranscriptionView";
//import AdminDashboard from "./pages/AdminDashboard";
import NotFoundPage from "./pages/NotFoundPage";
import AuthGuard from "./components/AuthGuard";

const queryClient = new QueryClient();

export default function App() {
    return (
        <DarkModeProvider>
            <QueryClientProvider client={queryClient}>
                <BrowserRouter>
                    <AuthProvider>
                        <Routes>
                            {/* Rotas públicas */}
                            <Route path="/login" element={<Login />} />
                            <Route path="/register" element={<Register />} />

                            {/* Rotas protegidas com Layout */}
                            <Route element={<Layout />}>
                                <Route index element={<Navigate to="/user" replace />} />
                                <Route path="/user" element={
                                    <AuthGuard>
                                        <UserDashboard />
                                    </AuthGuard>
                                } />
                                <Route path="/summary/:videoId" element={
                                    <AuthGuard>
                                        <SummaryView />
                                    </AuthGuard>
                                } />
                                <Route path="/transcription/:videoId" element={
                                    <AuthGuard>
                                        <TranscriptionView />
                                    </AuthGuard>
                                } />
                                {/* <Route path="/admin" element={
                                    <AuthGuard adminOnly>
                                        <AdminDashboard />
                                    </AuthGuard>
                                } /> */}
                            </Route>

                            {/* Rota 404 */}
                            <Route path="*" element={<NotFoundPage />} />
                        </Routes>
                    </AuthProvider>
                </BrowserRouter>
            </QueryClientProvider>
        </DarkModeProvider>
    );
}