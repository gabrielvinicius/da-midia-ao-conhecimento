import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { DarkModeProvider } from "./contexts/ DarkModeContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import UserDashboard from "./pages/UserDashboard";
import SummaryView from "./pages/SummaryView";
import TranscriptionView from "./pages/TranscriptionView";

export default function App() {
    return (
        <DarkModeProvider>
            <BrowserRouter>
                <AuthProvider>
                    <Layout>
                        <Routes>
                            <Route path="/login" element={<Login />} />
                            <Route path="/register" element={<Register />} />
                            <Route path="/user" element={<UserDashboard />} />
                            <Route path="/summary/:videoId" element={<SummaryView />} />
                            <Route path="/transcription/:videoId" element={<TranscriptionView />} />
                            <Route path="/" element={<UserDashboard />} />
                        </Routes>
                    </Layout>
                </AuthProvider>
            </BrowserRouter>
        </DarkModeProvider>
    );
}