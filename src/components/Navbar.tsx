import { useAuthContext } from "../contexts/AuthContext";
import { Link } from "react-router-dom";
import DarkModeToggle from "./DarkModeToggle";

export default function Navbar() {
    const { user, logout } = useAuthContext();

    return (
        <nav className="bg-white dark:bg-gray-800 shadow-sm">
            <div className="container mx-auto px-4 py-3 flex justify-between items-center">
                <Link to="/" className="text-xl font-bold">VideoSummarizer</Link>
                <div className="flex items-center gap-4">
                    <DarkModeToggle />
                    {user ? (
                        <>
                            <span className="text-sm">{user.email}</span>
                            <button onClick={logout} className="text-red-500 hover:underline">Sair</button>
                        </>
                    ) : (
                        <>
                            <Link to="/login" className="hover:underline">Login</Link>
                            <Link to="/register" className="hover:underline">Registrar</Link>
                        </>
                    )}
                </div>
            </div>
        </nav>
    );
}