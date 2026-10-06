import { Link } from "react-router-dom";

export default function NotFoundPage() {
    return (
        <div className="flex flex-col items-center justify-center h-screen bg-gray-50 dark:bg-gray-900">
            <h1 className="text-6xl font-bold text-gray-800 dark:text-white">404</h1>
            <p className="text-xl text-gray-600 dark:text-gray-300 mb-6">Página não encontrada</p>
            <Link
                to="/"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
                Voltar para o início
            </Link>
        </div>
    );
}