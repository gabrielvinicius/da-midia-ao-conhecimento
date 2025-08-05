// src/pages/UserDashboard.tsx
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import VideoCard from '../components/VideoCard';
import LoadingSpinner from '../components/LoadingSpinner';
import VideoUpload from '../components/VideoUpload';
import { getVideosByUser } from '../services/video.service';

export default function UserDashboard() {
    const {
        data: videos = [],
        isLoading,
        error,
        refetch,
    } = useQuery({
        queryKey: ['userVideos'],
        queryFn: getVideosByUser,
    });

    const handleUploadSuccess = () => {
        // Opcional: mostrar notificação de sucesso
        console.log('Vídeo enviado com sucesso!');
    };

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">Seus Vídeos</h1>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                    Total: {videos.length}
                </div>
            </div>

            <VideoUpload onUploadSuccess={handleUploadSuccess} />

            {isLoading ? (
                <LoadingSpinner />
            ) : error ? (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4 text-red-700 dark:text-red-300">
                    Erro ao carregar vídeos: {(error as Error).message}
                    <button
                        onClick={() => refetch()}
                        className="ml-2 text-blue-600 hover:text-blue-800 dark:text-blue-400"
                    >
                        Tentar novamente
                    </button>
                </div>
            ) : videos.length === 0 ? (
                <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
                    <svg
                        className="mx-auto h-16 w-16 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                        />
                    </svg>
                    <h3 className="mt-2 text-lg font-medium text-gray-900 dark:text-white">
                        Nenhum vídeo encontrado
                    </h3>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        Comece enviando seu primeiro vídeo
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {videos.map((video) => (
                        <Link to={`/summary/${video.id}`} key={video.id}>
                            <VideoCard video={video} />
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}