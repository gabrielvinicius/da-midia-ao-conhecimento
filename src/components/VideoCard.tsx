import React from "react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { MediaStatus, Video } from "../types";

interface VideoCardProps {
    video: Video;
    className?: string;
}

function getStatusColor(status: Video["status"]) {
    switch (status) {
        case MediaStatus.COMPLETED:
            return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300";
        case MediaStatus.PROCESSING:
            return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300";
        case MediaStatus.FAILED:
            return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
        default:
            return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300";
    }
}

function getStatusLabel(status: Video["status"]) {
    switch (status) {
        case MediaStatus.PROCESSING:
            return "Processando";
        case MediaStatus.COMPLETED:
            return "Concluído";
        case MediaStatus.FAILED:
            return "Falhou";
        default:
            return "";
    }
}

export default function VideoCard({ video, className = "" }: VideoCardProps) {
    return (
        <div className={`bg-white dark:bg-gray-800 p-4 rounded-lg shadow hover:shadow-md transition-shadow border border-gray-100 dark:border-gray-700 ${className}`}>
            <h3 className="font-semibold truncate mb-2" title={video.original_file_path}>{video.original_file_path}</h3>
            <div className="flex items-center justify-between">
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(video.status)}`}>
                    {getStatusLabel(video.status)}
                </span>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatDistanceToNow(new Date(video.created_at), {
                        addSuffix: true,
                        locale: ptBR,
                    })}
                </p>
            </div>
        </div>
    );
}