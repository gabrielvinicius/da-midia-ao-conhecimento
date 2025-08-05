import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import VideoCard from '../components/VideoCard'

export default function UserDashboard() {
    const [videos, setVideos] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchVideos = async () => {
            try {
                const res = await api.get('/videos/me')
                setVideos(res.data)
            } catch (err) {
                console.error(err)
            } finally {
                setLoading(false)
            }
        }

        fetchVideos()
    }, [])

    if (loading) return <div>Carregando...</div>

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-2xl font-bold mb-6">Seus Vídeos</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {videos.map(video => (
                    <Link to={`/summary/${video.id}`} key={video.id}>
                        <VideoCard video={video} />
                    </Link>
                ))}
            </div>
        </div>
    )
}