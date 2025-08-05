import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../services/api'
import ExportButtons from '../components/ExportButtons'

export default function SummaryView() {
    const { videoId } = useParams()
    const [summary, setSummary] = useState('')
    const [videoInfo, setVideoInfo] = useState(null)
    const [isLoading, setIsLoading] = useState(true)
    const navigate = useNavigate()

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true)

                // Busca o resumo
                const summaryResponse = await api.get(`/summaries/${videoId}`)
                setSummary(summaryResponse.data.text || 'Nenhum resumo disponível')

                // Busca informações do vídeo (opcional)
                const videoResponse = await api.get(`/videos/${videoId}`)
                setVideoInfo({
                    title: videoResponse.data.file_path || `Vídeo ${videoId.slice(0, 8)}`,
                    createdAt: videoResponse.data.created_at
                })
            } catch (error) {
                console.error(error)
            } finally {
                setIsLoading(false)
            }
        }

        fetchData()
    }, [videoId])

    // Função para exportar como PDF
    const exportAsPdf = () => {
        // Implementação de exportação para PDF
        alert('Exportação para PDF em desenvolvimento')
    }

    if (isLoading) return <div>Carregando resumo...</div>

    return (
        <div className="p-8 max-w-4xl mx-auto dark:bg-gray-900 min-h-screen">
            {/* Cabeçalho */}
            <div className="flex justify-between items-center mb-6">
                <button
                    onClick={() => navigate('/user')}
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

            {/* Conteúdo do resumo */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md mb-6">
                <h2 className="text-xl font-semibold mb-4 dark:text-white">Resumo:</h2>
                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{summary}</p>
            </div>

            {/* Botões de exportação */}
            <ExportButtons onExportTxt={() => {}} onExportPdf={exportAsPdf} />

            {/* Informações adicionais */}
            <div className="mt-6 text-sm text-gray-500 dark:text-gray-400">
                <p>ID do Vídeo: {videoId}</p>
            </div>
        </div>
    )
}