// src/pages/SummaryView.tsx
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import ExportButtons from '../components/ExportButtons';
import LoadingSpinner from '../components/LoadingSpinner';

const fetchSummary = async (videoId: string) => {
    const res = await api.get(`/summaries/${videoId}`);
    return res.data;
};

const fetchVideoInfo = async (videoId: string) => {
    const res = await api.get(`/videos/${videoId}`);
    return res.data;
};

export default function SummaryView() {
    const { videoId } = useParams<{ videoId: string }>();
    const navigate = useNavigate();

    const {
        data: summary,
        isLoading: loadingSummary,
        error: summaryError,
    } = useQuery({
        queryKey: ['summary', videoId],
        queryFn: () => fetchSummary(videoId!),
        enabled: !!videoId,
    });

    const {
        data: videoInfo,
        isLoading: loadingVideo,
        error: videoError,
    } = useQuery({
        queryKey: ['video', videoId],
        queryFn: () => fetchVideoInfo(videoId!),
        enabled: !!videoId,
    });

    const isLoading = loadingSummary || loadingVideo;
    const error = summaryError || videoError;

    if (isLoading) return <LoadingSpinner />;
    if (error) return <div>Erro ao carregar dados.</div>;

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
                <h2 className="text-xl font-semibold mb-4 dark:text-white">Resumo:</h2>
                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {summary?.text || 'Nenhum resumo disponível.'}
                </p>
            </div>

            <ExportButtons onExportTxt={() => {}} onExportPdf={exportAsPdf} />

            <div className="mt-6 text-sm text-gray-500 dark:text-gray-400">
                <p>ID do Vídeo: {videoId}</p>
            </div>
        </div>
    );
}