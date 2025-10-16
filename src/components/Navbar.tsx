import React from "react";
import { useAuthContext } from "@/contexts/AuthContext";
import { Link } from "react-router-dom";
import DarkModeToggle from "./DarkModeToggle";

export default function Navbar({ className = "" }: { className?: string }) {
    const { user, logout } = useAuthContext();

    return (
        <nav className={`bg-white dark:bg-gray-800 shadow-sm ${className}`}>
            <div className="container mx-auto px-4 py-3 flex justify-between items-center">
                <Link to="/" className="text-xl font-bold" aria-label="Página inicial">
                    Resumidor de Vídeos
                </Link>
                <div className="flex items-center gap-4">
                    <DarkModeToggle />
                    {user ? (
                        <>
                            <span className="text-sm" aria-label="Usuário logado">{user.email}</span>
                            <button
                                type="button"
                                onClick={logout}
                                className="text-red-500 hover:underline"
                                aria-label="Sair"
                            >
                                Sair
                            </button>
                        </>
                    ) : (
                        <>
                            <Link to="/login" className="hover:underline" aria-label="Fazer login">
                                Entrar
                            </Link>
                            <Link to="/register" className="hover:underline" aria-label="Registrar">
                                Cadastrar
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </nav>
    );
}