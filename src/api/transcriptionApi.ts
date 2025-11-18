import api from "@/lib/api";
import { Transcription } from "../types";

export const getTranscriptionByMediaId = async (mediaId: string): Promise<Transcription> => {
  const response = await api.get(`/transcriptions/?media_id=${mediaId}`);
  return response.data;
};

export const transcribeAudio = async (
  audioFile: File,
  options?: {
    provider?: string;
    language?: string;
    wordTimestamps?: boolean;
  }
): Promise<any> => {
  const formData = new FormData();
  formData.append("audio_file", audioFile);
  
  if (options?.provider) {
    formData.append("provider", options.provider);
  }
  if (options?.language) {
    formData.append("language", options.language);
  }
  if (options?.wordTimestamps !== undefined) {
    formData.append("word_timestamps", options.wordTimestamps.toString());
  }

  const response = await api.post("/transcriptions/transcribe", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const reprocessTranscription = async (
  mediaId: string,
  options?: {
    provider?: string;
    language?: string;
    force?: boolean;
  }
): Promise<any> => {
  const formData = new FormData();
  formData.append("media_id", mediaId);
  
  if (options?.provider) {
    formData.append("provider", options.provider);
  }
  if (options?.language) {
    formData.append("language", options.language);
  }
  if (options?.force !== undefined) {
    formData.append("force", options.force.toString());
  }

  const response = await api.post("/transcriptions/reprocess", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export default { getTranscriptionByMediaId, transcribeAudio, reprocessTranscription };
