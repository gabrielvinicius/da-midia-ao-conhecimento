// src/pages/UserDashboard.tsx
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import VideoCard from '../components/VideoCard';
import LoadingSpinner from '../components/LoadingSpinner';

const fetchUserVideos = async (): Promise<Video[]> => {
    const res = await api.get('/videos/me');
    return res.data;
};

export default function UserDashboard() {
    const {
        data: videos = [],
        isLoading,
        error,
    } = useQuery<Video[]>({
        queryKey: ['userVideos'],
        queryFn: fetchUserVideos,
    });

    if (isLoading) return <LoadingSpinner />;
    if (error) return <div>Erro ao carregar vídeos.</div>;

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-2xl font-bold mb-6">Seus Vídeos</h1>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {videos.map((video) => (
                    <Link to={`/summary/${video.id}`} key={video.id}>
                        <VideoCard video={video} />
                    </Link>
                ))}
            </div>
        </div>
    );
}