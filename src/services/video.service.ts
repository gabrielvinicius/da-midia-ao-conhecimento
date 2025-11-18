// src/services/video.service.ts
import api, { buildApiUrl } from "@/lib/api";
import { Video } from "@/types";

export const getVideosByUser = async (): Promise<Video[]> => {
    const response = await api.get("/videos/me");
    return response.data;
};

export const getVideoById = async (id: string): Promise<Video> => {
    const response = await api.get(`/videos/${id}`);
    return response.data;
};

export const uploadVideo = async (file: File): Promise<Video> => {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await api.post("/videos/upload", formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
            // Opcional: para monitorar progresso
            onUploadProgress: (progressEvent) => {
                const percentCompleted = Math.round(
                    (progressEvent.loaded * 100) / progressEvent.total!
                );
                console.log(`Progresso do upload: ${percentCompleted}%`);
                // Aqui você poderia atualizar um estado para mostrar barra de progresso
            },
        });
        return response.data;
    } catch (error: any) {
        // Tratamento de erro mais específico
        if (error.response?.data?.detail) {
            throw new Error(error.response.data.detail);
        }
        throw new Error("Falha ao enviar vídeo. Tente novamente mais tarde.");
    }
};

export const deleteVideo = async (id: string): Promise<boolean> => {
    const response = await api.delete(`/videos/${id}`);
    return response.status === 204;
};

// Nova função para conectar ao SSE e escutar atualizações
export const subscribeToVideoEvents = (
    onVideoUpdate: (video: Video) => void,
    onError: (error: Event) => void
): EventSource => {
    const eventSource = new EventSource(buildApiUrl('/videos/events'), {
        withCredentials: true,
    });

    // Escuta eventos de atualização
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'INITIAL' || data.type === 'UPDATE') {
            onVideoUpdate(data.video);
        }
    };

    // Escuta erros de conexão
    eventSource.onerror = onError;

    return eventSource;
};
