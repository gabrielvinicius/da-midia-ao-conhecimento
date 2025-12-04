// src/pages/UserDashboard.tsx
import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';
import VideoCard from '../components/VideoCard';
import LoadingSpinner from '../components/LoadingSpinner';
import VideoUpload from '../components/VideoUpload';
import { getVideosByUser, uploadVideo, subscribeToVideoEvents } from '@/services/video.service';
import { Video } from '@/types';

export default function UserDashboard() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const {
        data: videos = [],
        isLoading,
        error,
        refetch,
    } = useQuery({
        queryKey: ['userVideos'],
        queryFn: getVideosByUser,
    });

    // Mutation para upload de vídeo
    const uploadMutation = useMutation({
        mutationFn: uploadVideo,
        onSuccess: () => {
            // Invalida e refetch a lista de vídeos após o upload
            queryClient.invalidateQueries({ queryKey: ['userVideos'] });
            toast.success('Vídeo enviado com sucesso!');
        },
        onError: (error: any) => {
            toast.error(error.message || 'Falha ao enviar vídeo.');
        },
    });

    // Função que será passada para o componente VideoUpload
    const handleFileSelect = (file: File) => {
        uploadMutation.mutate(file);
    };

    // Efeito para carregar vídeos iniciais e configurar WebSocket
    useEffect(() => {
        // Configura a conexão WebSocket para atualizações em tempo real
        const ws = subscribeToVideoEvents(
            (data) => {
                // Se o evento for relevante (ex: conclusão de processamento), atualiza a lista
                // O payload exato depende da notificação do backend.
                // Assumindo que recebemos um objeto com type ou status
                
                // Simplesmente invalidamos a query para garantir dados frescos
                // (Poderíamos otimizar atualizando o cache localmente se o payload for completo)
                queryClient.invalidateQueries({ queryKey: ['userVideos'] });
            },
            (error) => {
                console.error('Erro na conexão WebSocket:', error);
            }
        );

        // Cleanup ao desmontar o componente
        return () => {
            ws.close();
        };
    }, [queryClient]);

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">Seus Vídeos</h1>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                    Total: {videos.length}
                </div>
            </div>
            {/* Passa a função handleFileSelect como onUpload */}
            <VideoUpload onUpload={handleFileSelect} />
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