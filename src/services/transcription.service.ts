import api from "./api";
import { Transcription } from "../types";

export const getTranscriptionByVideoId = async (
    videoId: string
): Promise<Transcription> => {
    const response = await api.get(`/transcriptions/${videoId}`);
    return response.data;
};

export const startTranscription = async (
    videoId: string
): Promise<{ message: string }> => {
    const response = await api.post(`/transcriptions/${videoId}`);
    return response.data;
};