// src/pages/SummaryView.tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthContext } from '../contexts/AuthContext';
import api from '@/lib/api';
import { toast } from 'react-toastify';
import { jsPDF } from 'jspdf';
import { saveAs } from 'file-saver';
import { getVideoById, subscribeToVideoEvents } from '@/services/video.service';

export default function SummaryView() {
    const { videoId } = useParams();
    const { user } = useAuthContext();
    const navigate = useNavigate();
    const [summary, setSummary] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [videoInfo, setVideoInfo] = useState({
        status: string;
        title: string;
        createdAt: string;
    } | null>(null);
    const [progress, setProgress] = useState<number>(0);
    const [estimatedTime, setEstimatedTime] = useState<number | null>(null);
    const [currentStage, setCurrentStage] = useState<string>('Processando...');

    // Busca resumo e informações do vídeo
    useEffect(() => {
        if (!videoId) return;

        const fetchData = async () => {
            try {
                setIsLoading(true);
                
                // Busca informações do vídeo
                const videoResponse = await getVideoById(videoId);
                setVideoInfo({
                    status: videoResponse.status,
                    title: videoResponse.filename || `Vídeo ${videoId.slice(0, 8)}`,
                    createdAt: videoResponse.created_at
                });

                // Tenta buscar a análise (resumo)
                try {
                    const analysisResponse = await api.get(`/text-analysis/media/${videoId}`);
                    // A estrutura do AnalyzeResponse contém 'summary' ou está dentro de 'topics'?
                    // Pelo código do backend, analysis.summary_md existe nos tópicos, ou overall_sentiment.
                    // Vamos assumir que o frontend espera um campo 'summary' ou 'content'.
                    // Se o AnalyzeResponse retornar o objeto Analysis completo, precisamos extrair.
                    // Por enquanto, vamos exibir o JSON ou um campo específico.
                    // O código anterior usava summaryResponse.data.content.
                    // Vamos adaptar para o novo formato.
                    
                    // Se houver tópicos com resumo, pegamos o primeiro ou concatenamos.
                    const topics = analysisResponse.data.topics || [];
                    if (topics.length > 0) {
                        setSummary(topics.map((t: any) => t.summary_md).join('\n\n'));
                    } else if (analysisResponse.data.diagnostics?.summary) {
                         setSummary(analysisResponse.data.diagnostics.summary);
                    } else {
                        setSummary(JSON.stringify(analysisResponse.data, null, 2));
                    }

                } catch (err) {
                    // Se der 404, significa que ainda não foi processado ou falhou
                    console.log("Análise ainda não disponível");
                }

                if (videoResponse.status === 'COMPLETED') {
                    setProgress(100);
                    setCurrentStage('Concluído');
                }
            } catch (error) {
                toast.error('Falha ao carregar informações do vídeo');
                navigate('/user');
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, [videoId, navigate]);

    // Efeito para WebSocket
    useEffect(() => {
        if (!videoId || videoInfo?.status === 'COMPLETED') return;

        const ws = subscribeToVideoEvents(
            (data) => {
                // Lógica de atualização baseada nos eventos do WebSocket
                // O backend envia notificações. O formato exato depende do NotificationTaskPayload.
                // Se for um evento de progresso:
                if (data.media_id === videoId) {
                     if (data.status === 'COMPLETED') {
                        setVideoInfo(prev => prev ? { ...prev, status: 'COMPLETED' } : null);
                        setProgress(100);
                        setCurrentStage('Concluído');
                        // Recarrega o resumo
                        api.get(`/text-analysis/media/${videoId}`).then(res => {
                             const topics = res.data.topics || [];
                             if (topics.length > 0) {
                                setSummary(topics.map((t: any) => t.summary_md).join('\n\n'));
                             }
                        });
                     } else if (data.type === 'progress') {
                        // Se o backend enviar progresso detalhado
                        setProgress(data.progress || 0);
                        setCurrentStage(data.stage || 'Processando...');
                     }
                }
            },
            (error) => {
                console.error('Erro no WebSocket:', error);
            }
        );

        return () => {
            ws.close();
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
        doc.setFontSize(12);
        doc.text(`Resumo do Vídeo: ${videoInfo?.title || videoId}`, 10, 10);
        doc.text(`Data: ${videoInfo?.createdAt ? new Date(videoInfo.createdAt).toLocaleDateString() : ''}`, 10, 16);
        const splitText = doc.splitTextToSize(summary, 180);
        doc.setFontSize(10);
        doc.text(splitText, 10, 26);
        doc.save(`resumo-${videoId}.pdf`);
    };

    const handleBack = () => {
        navigate('/user');
    };

    return (
        <div className="p-8 max-w-4xl mx-auto dark:bg-gray-900 min-h-screen">
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
                <div className="w-8"></div>
            </div>
            {videoInfo?.createdAt && (
                <p className="text-gray-500 dark:text-gray-400 mb-6">
                    Criado em: {new Date(videoInfo.createdAt).toLocaleString()}
                </p>
            )}
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
                </div>
            )}
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
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
                {isLoading ? (
                    <div className="flex justify-center items-center h-40">
                        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
                    </div>
                ) : (
                    <pre className="whitespace-pre-wrap font-sans text-gray-800 dark:text-gray-200">
            {summary || "Resumo não disponível."} 
          </pre>
                )}
            </div>
            <div className="mt-6 text-sm text-gray-500 dark:text-gray-400">
                <p>Gerado para: {user?.email}</p>
                <p>ID do Vídeo: {videoId}</p>
            </div>
        </div>
    );
}