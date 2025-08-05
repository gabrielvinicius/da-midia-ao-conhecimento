// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { DarkModeProvider } from "./contexts/DarkModeContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import UserDashboard from "./pages/UserDashboard";
import SummaryView from "./pages/SummaryView";
import TranscriptionView from "./pages/TranscriptionView";
import AdminDashboard from "./components/AdminDashboard";
import NotFoundPage from "./pages/NotFoundPage";
import AuthGuard from "./components/AuthGuard";

export default function App() {
    return (
        <DarkModeProvider>
            <BrowserRouter>
                <AuthProvider>
                    <Layout>
                        <Routes>
                            <Route path="/login" element={<Login />} />
                            <Route path="/register" element={<Register />} />
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
                            <Route path="/admin" element={
                                <AuthGuard adminOnly>
                                    <AdminDashboard />
                                </AuthGuard>
                            } />
                            <Route path="/" element={<Navigate to="/user" />} />
                            <Route path="*" element={<NotFoundPage />} />
                        </Routes>
                    </Layout>
                </AuthProvider>
            </BrowserRouter>
        </DarkModeProvider>
    );
}