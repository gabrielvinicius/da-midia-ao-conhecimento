"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { VideoCard } from "./video-card";

type Video = {
    id: string;
    title: string;
    created_at: string;
    status: "processing" | "completed" | "failed";
};

export function VideoList() {
    const [videos, setVideos] = useState<Video[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchVideos() {
            try {
                const res = await api.get("/videos/");
                setVideos(res.data);
            } catch (err) {
                console.error("Erro ao buscar vídeos", err);
            } finally {
                setLoading(false);
            }
        }

        fetchVideos();
    }, []);

    if (loading) return <p>Carregando vídeos...</p>;
    if (videos.length === 0) return <p>Nenhum vídeo encontrado.</p>;

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {videos.map((video) => (
                <VideoCard key={video.id} video={video} />
            ))}
        </div>
    );
}
