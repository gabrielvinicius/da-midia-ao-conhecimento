import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import api from '../services/api'

export default function TranscriptionView() {
    const { videoId } = useParams()
    const [transcription, setTranscription] = useState('')
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchTranscription = async () => {
            try {
                const res = await api.get(`/transcriptions/${videoId}`)
                setTranscription(res.data.text || 'Nenhuma transcrição disponível')
            } catch (err) {
                console.error(err)
                setTranscription('Falha ao carregar a transcrição')
            } finally {
                setLoading(false)
            }
        }

        fetchTranscription()
    }, [videoId])

    return (
        <div className="p-8 max-w-4xl mx-auto dark:bg-gray-900 min-h-screen">
            <h1 className="text-2xl font-bold mb-6 dark:text-white">
                Transcrição do Vídeo: {videoId}
            </h1>

            {loading ? (
                <p>Carregando transcrição...</p>
            ) : (
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
                    <h2 className="text-xl font-semibold mb-4 dark:text-white">Conteúdo:</h2>
                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{transcription}</p>
                </div>
            )}
        </div>
    )
}