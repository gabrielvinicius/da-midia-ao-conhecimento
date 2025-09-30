import api from "../../../lib/api";
import { Transcription } from "../../../types";

export const getTranscriptionByMediaId = async (mediaId: string): Promise<Transcription | null> => {
  try {
    const response = await api.get<Transcription>(`/transcriptions/?media_id=${mediaId}`);
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.status === 404) {
      // A 404 is not necessarily an error, it just means the transcription isn't ready or doesn't exist.
      return null;
    }
    // For other errors, let the global handler deal with it.
    throw error;
  }
};
