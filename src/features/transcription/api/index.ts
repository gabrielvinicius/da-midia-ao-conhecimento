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

export const reprocessTranscription = async (
  mediaId: string,
  options?: {
    provider?: string;
    language?: string;
    force?: boolean;
  }
): Promise<any> => {
  console.log('🔄 Reprocessando transcrição para mídia:', mediaId);
  
  const formData = new FormData();
  formData.append('media_id', mediaId);
  
  if (options?.provider) {
    formData.append('provider', options.provider);
  }
  if (options?.language) {
    formData.append('language', options.language);
  }
  if (options?.force !== undefined) {
    formData.append('force', options.force.toString());
  }

  const response = await api.post('/transcriptions/reprocess', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  console.log('✅ Reprocessamento de transcrição iniciado:', response.data);
  return response.data;
};
