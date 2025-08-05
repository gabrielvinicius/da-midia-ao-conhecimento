import api from "./api";
import { Summary } from "../types";

export const getSummaryByVideoId = async (
    videoId: string
): Promise<Summary> => {
    const response = await api.get(`/summaries/${videoId}`);
    return response.data;
};

export const generateSummary = async (
    transcriptionId: string
): Promise<Summary> => {
    const response = await api.post(
        `/summaries/${transcriptionId}/summarization`
    );
    return response.data;
};