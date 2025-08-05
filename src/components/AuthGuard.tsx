import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import type { User } from "../types";

interface AuthGuardProps {
    children: React.ReactNode;
    adminOnly?: boolean;
}

export default function AuthGuard({ children, adminOnly = false }: AuthGuardProps) {
    const { User, loading } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (!loading && !User) {
            navigate("/login");
        }

        if (!loading && adminOnly && user?.role !== "admin") {
            navigate("/user");
        }
    }, [user, loading, navigate, adminOnly]);

    if (loading) {
        return (
            <div className="flex justify-center items-center h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    return <>{children}</>;
}