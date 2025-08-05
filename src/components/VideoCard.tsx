// src/components/VideoCard.tsx
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Video } from '../types';

interface VideoCardProps {
    video: Video;
}

export default function VideoCard({ video }: VideoCardProps) {
    // Determina a cor do status com base no estado
    const getStatusColor = () => {
        switch (video.status) {
            case 'COMPLETED':
                return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
            case 'PROCESSING':
                return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
            case 'FAILED':
                return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
            default:
                return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow hover:shadow-md transition-shadow border border-gray-100 dark:border-gray-700">
            <h3 className="font-semibold truncate mb-2">{video.file_path}</h3>

            <div className="flex items-center justify-between">
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor()}`}>
                    {video.status === 'UPLOADED' && 'Carregado'}
                    {video.status === 'PROCESSING' && 'Processando'}
                    {video.status === 'COMPLETED' && 'Concluído'}
                    {video.status === 'FAILED' && 'Falhou'}
                </span>

                <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatDistanceToNow(new Date(video.created_at), {
                        addSuffix: true,
                        locale: ptBR
                    })}
                </p>
            </div>
        </div>
    );
}