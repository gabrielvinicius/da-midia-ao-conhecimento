// src/pages/SummaryView.tsx
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { getSummaryByVideoId } from '../services/summary.service';
import { getVideoById } from '../services/video.service';
import ExportButtons from '../components/ExportButtons';
import LoadingSpinner from '../components/LoadingSpinner';

export default function SummaryView() {
    const { videoId } = useParams<{ videoId: string }>();
    const navigate = useNavigate();

    const {
        data: summary,
        isLoading: loadingSummary,
        error: summaryError,
    } = useQuery({
        queryKey: ['summary', videoId],
        queryFn: () => getSummaryByVideoId(videoId!),
        enabled: !!videoId,
        retry: (failureCount, error) => {
            // Se o vídeo está em processamento, tente novamente algumas vezes
            if ((error as any)?.response?.status === 404 && failureCount < 3) {
                return true;
            }
            return false;
        },
        retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000), // Exponential backoff
    });

    const {
        data: videoInfo,
        isLoading: loadingVideo,
        error: videoError,
    } = useQuery({
        queryKey: ['video', videoId],
        queryFn: () => getVideoById(videoId!),
        enabled: !!videoId,
    });

    const isLoading = loadingSummary || loadingVideo;
    const error = summaryError || videoError;

    if (isLoading) return <LoadingSpinner />;

    if (error) {
        return (
            <div className="p-8 max-w-4xl mx-auto dark:bg-gray-900 min-h-screen">
                <div className="flex justify-between items-center mb-6">
                    <button
                        onClick={() => navigate('/user')}
                        className="flex items-center text-blue-500 hover:text-blue-700 dark:text-blue-400"
                    >
                        ← Voltar
                    </button>
                    <h1 className="text-2xl font-bold dark:text-white">
                        Erro ao carregar resumo
                    </h1>
                </div>

                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
                    <h2 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
                        {videoInfo?.status === 'PROCESSING'
                            ? 'Processamento em andamento'
                            : 'Erro ao carregar resumo'}
                    </h2>

                    <p className="text-gray-700 dark:text-gray-300 mb-4">
                        {videoInfo?.status === 'PROCESSING'
                            ? 'Seu vídeo ainda está sendo processado. Atualize esta página em alguns minutos.'
                            : 'Não foi possível carregar o resumo deste vídeo.'}
                    </p>

                    <div className="flex space-x-4">
                        <button
                            onClick={() => window.location.reload()}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                        >
                            Tentar novamente
                        </button>
                        <button
                            onClick={() => navigate('/user')}
                            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                        >
                            Voltar para lista
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const exportAsPdf = () => alert('Exportação para PDF em desenvolvimento');

    return (
        <div className="p-8 max-w-4xl mx-auto dark:bg-gray-900 min-h-screen">
            <div className="flex justify-between items-center mb-6">
                <button
                    onClick={() => navigate('/user')}
                    className="flex items-center text-blue-500 hover:text-blue-700 dark:text-blue-400"
                >
                    ← Voltar
                </button>
                <h1 className="text-2xl font-bold dark:text-white">
                    Resumo do Vídeo: {videoInfo?.file_path || `Vídeo ${videoId}`}
                </h1>
                <div className="w-8"></div>
            </div>

            {videoInfo?.created_at && (
                <p className="text-gray-500 dark:text-gray-400 mb-6">
                    Criado em: {new Date(videoInfo.created_at).toLocaleString()}
                </p>
            )}

            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-6">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold dark:text-white">Resumo:</h2>
                    {videoInfo?.status === 'PROCESSING' && (
                        <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">
                            Processando...
                        </span>
                    )}
                </div>
                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {summary?.text || 'O resumo está sendo gerado. Atualize esta página em alguns minutos.'}
                </p>
            </div>

            {videoInfo?.status === 'COMPLETED' && (
                <ExportButtons onExportTxt={() => {}} onExportPdf={exportAsPdf} />
            )}

            <div className="mt-6 text-sm text-gray-500 dark:text-gray-400">
                <p>ID do Vídeo: {videoId}</p>
            </div>
        </div>
    );
}