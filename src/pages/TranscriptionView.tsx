// src/pages/TranscriptionView.tsx
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { getTranscriptionByVideoId } from '../services/transcription.service';
import LoadingSpinner from '../components/LoadingSpinner';

export default function TranscriptionView() {
    const { videoId } = useParams<{ videoId: string }>();

    const {
        data: transcription,
        isLoading,
        error,
    } = useQuery({
        queryKey: ['transcription', videoId],
        queryFn: () => getTranscriptionByVideoId(videoId!),
        enabled: !!videoId,
    });

    if (isLoading) return <LoadingSpinner />;
    if (error) return <div>Erro ao carregar transcrição.</div>;

    return (
        <div className="p-8 max-w-4xl mx-auto dark:bg-gray-900 min-h-screen">
            <h1 className="text-2xl font-bold mb-6 dark:text-white">
                Transcrição do Vídeo: {videoId}
            </h1>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
                <h2 className="text-xl font-semibold mb-4 dark:text-white">Conteúdo:</h2>
                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {transcription?.text || 'Nenhuma transcrição disponível.'}
                </p>
            </div>
        </div>
    );
}