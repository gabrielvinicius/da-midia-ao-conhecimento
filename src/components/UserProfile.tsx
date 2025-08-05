import React from "react";
import { useAuthContext } from "@/contexts/AuthContext";

interface UserProfileProps {
    className?: string;
}

export default function UserProfile({ className = "" }: UserProfileProps) {
    const { user } = useAuthContext();

    if (!user) {
        return (
            <div className={`bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-100 dark:border-gray-700 text-center ${className}`}>
                <p className="text-gray-500 dark:text-gray-400">Nenhum usuário autenticado.</p>
            </div>
        );
    }

    return (
        <div className={`bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-100 dark:border-gray-700 ${className}`}>
            <h4 className="text-lg font-semibold mb-2">Perfil</h4>
            <div className="flex flex-col gap-2">
                <div>
                    <span className="font-medium">Email:</span> {user.email}
                </div>
                {user.email && (
                    <div>
                        <span className="font-medium">Nome:</span> {user.email}
                    </div>
                )}
                {user.role && (
                    <div>
                        <span className="font-medium">Tipo:</span> {user.role}
                    </div>
                )}
            </div>
        </div>
    );
}