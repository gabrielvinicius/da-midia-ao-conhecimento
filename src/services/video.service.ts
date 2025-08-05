import api from "./api";
import { Video } from "../types";

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

    const response = await api.post("/videos/upload", formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
    });

    return response.data;
};

export const deleteVideo = async (id: string): Promise<boolean> => {
    const response = await api.delete(`/videos/${id}`);
    return response.status === 204;
};