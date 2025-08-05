import { formatDistanceToNow } from 'date-fns';

interface Video {
    id: string;
    file_path: string;
    status: string;
    created_at: string;
}

interface VideoCardProps {
    video: Video;
}

export default function VideoCard({ video }: VideoCardProps) {
    return (
        <div className="bg-white dark:bg-gray-800 p-4 rounded shadow hover:shadow-md transition-shadow">
            <h3 className="font-semibold truncate">{video.file_path}</h3>
            <p>Status: <span className="capitalize">{video.status.toLowerCase()}</span></p>
            <p className="text-xs text-gray-500 mt-2">
                {formatDistanceToNow(new Date(video.created_at))} atrás
            </p>
        </div>
    );
}