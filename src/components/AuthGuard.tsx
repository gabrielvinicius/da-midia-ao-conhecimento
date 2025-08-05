import React, { useEffect } from "react";
import { useAuthContext } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";

interface AuthGuardProps {
    children: React.ReactNode;
    adminOnly?: boolean;
}

export default function AuthGuard({ children, adminOnly = false }: AuthGuardProps) {
    const { user, loading } = useAuthContext();
    const navigate = useNavigate();

    useEffect(() => {
        if (!loading) {
            if (!user) {
                navigate("/login", { replace: true });
            } else if (adminOnly && user.role !== "admin") {
                navigate("/user", { replace: true });
            }
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