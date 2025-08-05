import React from "react";

interface VideoPlayerProps {
    videoId: string;
    src: string;
    type?: string;
    className?: string;
}

export default function VideoPlayer({
                                        videoId,
                                        src,
                                        type = "video/mp4",
                                        className = "",
                                    }: VideoPlayerProps) {
    return (
        <div className={`w-full max-w-3xl mx-auto ${className}`}>
            <video
                id={`video-${videoId}`}
                controls
                className="w-full rounded-lg shadow-md"
                aria-label={`Player do vídeo ${videoId}`}
            >
                <source src={src} type={type} />
                Seu navegador não suporta o elemento de vídeo.
            </video>
        </div>
    );
}