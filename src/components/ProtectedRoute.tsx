"use client";

import React, { ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

interface ProtectedRouteProps {
    children: ReactNode;
    redirectTo?: string;
}

export function ProtectedRoute({ children, redirectTo = "/login" }: ProtectedRouteProps) {
    const router = useRouter();
    const [authorized, setAuthorized] = useState(false);

    useEffect(() => {
        const token = getToken();
        if (!token) {
            router.replace(redirectTo);
        } else {
            setAuthorized(true);
        }
    }, [router, redirectTo]);

    if (!authorized) return null;

    return <>{children}</>;
}
