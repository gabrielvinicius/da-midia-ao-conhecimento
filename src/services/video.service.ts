// src/services/video.service.ts
import api, { buildWsUrl } from "@/lib/api";
import { Media } from "@/types";

// Using 'Media' type as the canonical type. 'Video' legacy type is alias to Media in types.ts

export const getVideosByUser = async (): Promise<Media[]> => {
    const response = await api.get("/media/");
    return response.data;
};

export const getVideoById = async (id: string): Promise<Media> => {
    const response = await api.get(`/media/${id}`);
    return response.data;
};

export const uploadVideo = async (file: File): Promise<Media> => {
    const formData = new FormData();
    formData.append("file", file);

    try {
        // Using default 'local' storage provider. 
        // In the future, this service could accept provider options.
        const response = await api.post("/media/?storage_provider=local", formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
            onUploadProgress: (progressEvent) => {
                if (progressEvent.total) {
                    const percentCompleted = Math.round(
                        (progressEvent.loaded * 100) / progressEvent.total
                    );
                    console.log(`Progresso do upload: ${percentCompleted}%`);
                }
            },
        });
        return response.data;
    } catch (error: any) {
        if (error.response?.data?.detail) {
            throw new Error(error.response.data.detail);
        }
        throw new Error("Falha ao enviar mídia. Tente novamente mais tarde.");
    }
};

export const deleteVideo = async (id: string): Promise<boolean> => {
    const response = await api.delete(`/media/${id}`);
    return response.status === 204;
};

// WebSocket implementation replacing legacy SSE
export const subscribeToVideoEvents = (
    onUpdate: (data: any) => void,
    onError: (error: Event) => void
): WebSocket => {
    const wsUrl = buildWsUrl('/ws/notifications');
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        try {
            // The backend sends simple text or JSON. Assuming JSON for structured updates.
            // Currently backend sends: "Server received: ..." or could send notification JSON.
            // This is a placeholder for the real notification logic.
            const data = JSON.parse(event.data);
            onUpdate(data);
        } catch (e) {
            // If not JSON, pass raw data
            onUpdate(event.data);
        }
    };

    ws.onerror = onError;
    
    // Handle auth if needed (cookies are sent automatically by browser)
    
    return ws;
};