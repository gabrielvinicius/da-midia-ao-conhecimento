"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

export function useAuth(redirectTo: string = "/login") {
    const router = useRouter();

    useEffect(() => {
        const token = getToken();

        if (!token) {
            router.replace(redirectTo);
        }
    }, [router, redirectTo]);
}
