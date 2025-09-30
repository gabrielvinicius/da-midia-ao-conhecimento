import api from "@/lib/api";
import { Transcription } from "@/types";
import { GetPaginatedDataParams } from "@/features/admin/api"; // Assuming this is a shared type

export const getTranscriptionByMediaId = async (mediaId: string): Promise<Transcription | null> => {
  try {
    const response = await api.get<Transcription>(`/transcriptions/?media_id=${mediaId}`);
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.status === 404) {
      return null;
    }
    throw error;
  }
};

export const updateSpeakerAliases = async (transcriptionId: string, aliases: Record<string, string>): Promise<Transcription> => {
  const response = await api.put<Transcription>(`/transcriptions/${transcriptionId}/speakers`, { aliases });
  return response.data;
};
