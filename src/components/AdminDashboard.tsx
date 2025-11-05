import { MediaStatus, MediaType } from "@/types";
// src/components/AdminDashboard.tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import VideoCard from "./VideoCard";

export default function AdminDashboard() {
    const [activeTab, setActiveTab] = useState("videos");

    return (
        <div className="p-8 max-w-6xl mx-auto">
            <h1 className="text-3xl font-bold mb-8">Painel Administrativo</h1>
            <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
                <nav className="flex space-x-8">
                    {["videos", "users", "analytics"].map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`py-4 px-1 border-b-2 font-medium text-sm ${
                                activeTab === tab
                                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                                    : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                            }`}
                        >
                            {tab === "videos" && "Vídeos"}
                            {tab === "users" && "Usuários"}
                            {tab === "analytics" && "Estatísticas"}
                        </button>
                    ))}
                </nav>
            </div>

            <div className="mt-6">
                {activeTab === "videos" && (
                    <div>
                        <h2 className="text-xl font-semibold mb-4">Últimos Vídeos</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <Link to={`/summary/${i}`} key={i}>
                                    <VideoCard
                                        video={{
                                            id: i.toString(),
                                            user_id: "1",
                                            media_type: MediaType.VIDEO,
                                            original_file_path: `video${i}.mp4`,
                                            status: MediaStatus.COMPLETED,
                                            created_at: new Date().toISOString(),
                                        }}
                                    />
                                </Link>
                            ))}
                        </div>
                    </div>
                )}

                {activeTab === "users" && (
                    <div>
                        <h2 className="text-xl font-semibold mb-4">Usuários Registrados</h2>
                        <div className="overflow-x-auto">
                            <table className="min-w-full bg-white dark:bg-gray-800 rounded-lg overflow-hidden shadow">
                                <thead className="bg-gray-100 dark:bg-gray-700">
                                <tr>
                                    <th className="py-3 px-4 text-left">Email</th>
                                    <th className="py-3 px-4 text-left">Data de Registro</th>
                                    <th className="py-3 px-4 text-left">Status</th>
                                </tr>
                                </thead>
                                <tbody>
                                {[1, 2, 3, 4, 5].map((i) => (
                                    <tr key={i} className="border-t dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750">
                                        <td className="py-3 px-4">usuario{i}@exemplo.com</td>
                                        <td className="py-3 px-4">2023-08-{i.toString().padStart(2, '0')}</td>
                                        <td className="py-3 px-4">
                                                <span className="inline-block px-2 py-1 text-xs font-semibold bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-full">
                                                    Ativo
                                                </span>
                                        </td>
                                    </tr>
                                ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {activeTab === "analytics" && (
                    <div>
                        <h2 className="text-xl font-semibold mb-4">Estatísticas do Sistema</h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {[
                                { label: "Vídeos Processados", value: "1.234", color: "blue" },
                                { label: "Usuários Ativos", value: "56", color: "green" },
                                { label: "Tempo Médio", value: "2.5 min", color: "purple" },
                            ].map((stat) => (
                                <div key={stat.label} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
                                    <h3 className="text-lg font-medium text-gray-500 dark:text-gray-400">{stat.label}</h3>
                                    <p className={`mt-2 text-3xl font-bold text-${stat.color}-600`}>{stat.value}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}