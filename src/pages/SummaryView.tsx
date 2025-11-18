// src/pages/SummaryView.tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthContext } from '../contexts/AuthContext';
import api from '@/lib/api';
import { buildApiUrl } from '@/lib/api';
import { toast } from 'react-toastify';
import { jsPDF } from 'jspdf';
import { saveAs } from 'file-saver';

export default function SummaryView() {
    const { videoId } = useParams();
    const { user } = useAuthContext();
    const navigate = useNavigate();
    const [summary, setSummary] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [videoInfo, setVideoInfo] = useState<{
        status: string;
        title: string;
        createdAt: string;
    } | null>(null);
    // Novo estado para progresso
    const [progress, setProgress] = useState<number>(0);
    const [estimatedTime, setEstimatedTime] = useState<number | null>(null);
    const [currentStage, setCurrentStage] = useState<string>('Processando...');

    // Busca resumo e informações do vídeo
    useEffect(() => {
        if (!videoId) return;

        const fetchData = async () => {
            try {
                setIsLoading(true);
                // Busca o resumo
                const summaryResponse = await api.get(`/summaries/${videoId}`);
                setSummary(summaryResponse.data.content);
                // Busca informações do vídeo (opcional)
                const videoResponse = await api.get(`/videos/${videoId}`);
                setVideoInfo({
                    status: "",
                    title: videoResponse.data.file_name || `Vídeo ${videoId.slice(0, 8)}`,
                    createdAt: videoResponse.data.created_at
                });
                // Se o vídeo já está completo, seta progresso para 100%
                if (videoResponse.data.status === 'COMPLETED') {
                    setProgress(100);
                    setCurrentStage('Concluído');
                }
            } catch (error) {
                toast.error('Falha ao carregar resumo');
                navigate('/user');
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, [videoId, navigate]);

    // Efeito para configurar o SSE e escutar eventos de progresso
    useEffect(() => {
        if (!videoId || videoInfo?.status === 'COMPLETED') return;

        const eventSource = new EventSource(buildApiUrl('/videos/events'));

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'UPDATE' && data.video.id === videoId) {
                // Atualiza as informações do vídeo
                setVideoInfo(prev => ({
                    ...prev!,
                    status: data.video.status
                }));
                // Se o status mudou para COMPLETED, atualiza o progresso
                if (data.video.status === 'COMPLETED') {
                    setProgress(100);
                    setCurrentStage('Concluído');
                }
            }

            // Escuta eventos específicos de progresso
            if (data.video_id === videoId && data.type === 'transcription_progress') {
                setProgress(data.progress);
                setCurrentStage('Transcrevendo...');
                if (data.estimated_total_seconds) {
                    setEstimatedTime(data.estimated_total_seconds);
                }
            }

            if (data.video_id === videoId && data.type === 'summarization_progress') {
                setProgress(data.progress);
                setCurrentStage('Gerando Resumo...');
                if (data.estimated_total_seconds) {
                    setEstimatedTime(data.estimated_total_seconds);
                }
            }
        };

        eventSource.onerror = (error) => {
            console.error('Erro na conexão SSE:', error);
            // Opcional: Tentar reconectar ou mostrar notificação ao usuário
        };

        // Cleanup ao desmontar o componente
        return () => {
            eventSource.close();
        };
    }, [videoId, videoInfo?.status]);

    // Exportar como TXT
    const exportAsTxt = () => {
        const blob = new Blob([summary], { type: 'text/plain;charset=utf-8' });
        saveAs(blob, `resumo-${videoId}.txt`);
    };

    // Exportar como PDF
    const exportAsPdf = () => {
        const doc = new jsPDF();
        // Cabeçalho com informações do vídeo
        doc.setFontSize(12);
        doc.text(`Resumo do Vídeo: ${videoInfo?.title || videoId}`, 10, 10);
        doc.text(`Data: ${videoInfo?.createdAt ? new Date(videoInfo.createdAt).toLocaleDateString() : ''}`, 10, 16);
        // Conteúdo do resumo (com quebra de linhas)
        const splitText = doc.splitTextToSize(summary, 180);
        doc.setFontSize(10);
        doc.text(splitText, 10, 26);
        doc.save(`resumo-${videoId}.pdf`);
    };

    // Voltar para a lista de vídeos
    const handleBack = () => {
        navigate('/user');
    };

    return (
        <div className="p-8 max-w-4xl mx-auto dark:bg-gray-900 min-h-screen">
            {/* Cabeçalho */}
            <div className="flex justify-between items-center mb-6">
                <button
                    onClick={handleBack}
                    className="flex items-center text-blue-500 hover:text-blue-700 dark:text-blue-400"
                >
                    ← Voltar
                </button>
                <h1 className="text-2xl font-bold dark:text-white">
                    Resumo do Vídeo: {videoInfo?.title || videoId}
                </h1>
                <div className="w-8"></div> {/* Espaçamento */}
            </div>
            {/* Data de criação */}
            {videoInfo?.createdAt && (
                <p className="text-gray-500 dark:text-gray-400 mb-6">
                    Criado em: {new Date(videoInfo.createdAt).toLocaleString()}
                </p>
            )}
            {/* Barra de Progresso (aparece apenas se estiver processando) */}
            {videoInfo?.status !== 'COMPLETED' && (
                <div className="mb-6">
                    <div className="flex justify-between mb-2">
                        <span className="text-sm font-medium dark:text-white">{currentStage}</span>
                        <span className="text-sm font-medium dark:text-white">{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                        <div
                            className="bg-blue-600 h-2.5 rounded-full"
                            style={{ width: `${progress}%` }}
                        ></div>
                    </div>
                    {estimatedTime && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            Tempo estimado: {Math.ceil(estimatedTime / 60)} minutos
                        </p>
                    )}
                </div>
            )}
            {/* Botões de Exportação */}
            <div className="flex flex-wrap gap-3 mb-6">
                <button
                    onClick={exportAsTxt}
                    className="bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 px-4 py-2 rounded flex items-center"
                >
                    <span className="mr-2">📄</span> Exportar como TXT
                </button>
                <button
                    onClick={exportAsPdf}
                    className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded flex items-center"
                >
                    <span className="mr-2">📑</span> Exportar como PDF
                </button>
            </div>
            {/* Conteúdo do Resumo */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
                {isLoading ? (
                    <div className="flex justify-center items-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
                    </div>
                ) : (
                    <pre className="whitespace-pre-wrap font-sans text-gray-800 dark:text-gray-200">
            {summary}
          </pre>
                )}
            </div>
            {/* Rodapé com informações do usuário */}
            <div className="mt-6 text-sm text-gray-500 dark:text-gray-400">
                <p>Gerado para: {user?.email}</p>
                <p>ID do Vídeo: {videoId}</p>
            </div>
        </div>
    );
}
