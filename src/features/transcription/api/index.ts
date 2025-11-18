import api from "@/lib/api";
import { Transcription, TranscriptionResult, TranscriptionSegment, TranscriptionStatus } from "@/types";

interface RawTranscriptionSegment {
  start?: number;
  end?: number;
  text?: string;
  speaker?: string | null;
}

interface RawTranscriptionResponse {
  id: string;
  media_id: string;
  status: TranscriptionStatus;
  provider?: string | null;
  created_at: string;
  processed_at?: string | null;
  error_message?: string | null;
  text?: string | null;
  segments?: RawTranscriptionSegment[] | null;
  speaker_aliases?: Record<string, string>;
}

const normalizeSegments = (segments: RawTranscriptionSegment[] = []): TranscriptionSegment[] =>
  segments.map((segment) => ({
    start: Number(segment.start ?? 0),
    end: Number(segment.end ?? 0),
    text: segment.text ?? "",
    speaker: segment.speaker ?? undefined,
  }));

const adaptTranscription = (payload: RawTranscriptionResponse): Transcription => {
  const segments = normalizeSegments(payload.segments ?? []);
  const diarized = segments.some((segment) => Boolean(segment.speaker));
  const result: TranscriptionResult = {
    text: payload.text ?? "",
    segments,
    diarized,
  };

  return {
    id: payload.id,
    media_id: payload.media_id,
    status: payload.status,
    provider: payload.provider ?? null,
    created_at: payload.created_at,
    processed_at: payload.processed_at ?? null,
    error_message: payload.error_message ?? null,
    result,
    speaker_aliases: payload.speaker_aliases ?? {},
    text: payload.text ?? null,
  };
};

export const getTranscriptionByMediaId = async (mediaId: string): Promise<Transcription | null> => {
  try {
    const response = await api.get<RawTranscriptionResponse>(`/transcriptions/?media_id=${mediaId}`);
    return adaptTranscription(response.data);
  } catch (error: any) {
    if (error.response && error.response.status === 404) {
      return null;
    }
    throw error;
  }
};

export const updateSpeakerAliases = async (transcriptionId: string, aliases: Record<string, string>): Promise<Transcription> => {
  const response = await api.put<RawTranscriptionResponse>(`/transcriptions/${transcriptionId}/speakers`, { aliases });
  return adaptTranscription(response.data);
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

export const getTranscriptionById = async (transcriptionId: string): Promise<Transcription> => {
  const response = await api.get<RawTranscriptionResponse>(`/transcriptions/${transcriptionId}`);
  return adaptTranscription(response.data);
};
