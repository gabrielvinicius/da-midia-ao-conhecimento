import api from "@/lib/api";
import { apiErrorStatus } from '@/lib/errors';
import { Transcription, TranscriptionSegment, TranscriptionStatus } from "@/types";

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
  content?: string | null;
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
  const resolvedText = payload.text ?? payload.content ?? "";

  return {
    id: payload.id,
    media_id: payload.media_id,
    status: payload.status,
    provider: payload.provider ?? null,
    created_at: payload.created_at,
    processed_at: payload.processed_at ?? null,
    error_message: payload.error_message ?? null,
    text: resolvedText,
    segments,
    speaker_aliases: payload.speaker_aliases ?? {},
  };
};

export const getTranscriptionByMediaId = async (mediaId: string): Promise<Transcription | null> => {
  try {
    const response = await api.get<RawTranscriptionResponse>(`/transcriptions/?media_id=${mediaId}`);
    return adaptTranscription(response.data);
  } catch (error) {
    if (apiErrorStatus(error) === 404) {
      return null;
    }
    throw error;
  }
};

export const updateSpeakerAliases = async (transcriptionId: string, aliases: Record<string, string>): Promise<Transcription> => {
  const response = await api.put<RawTranscriptionResponse>(
    `/transcriptions/${transcriptionId}/speaker-aliases`,
    { aliases }
  );
  return adaptTranscription(response.data);
};

export const getTranscriptionById = async (transcriptionId: string): Promise<Transcription> => {
  const response = await api.get<RawTranscriptionResponse>(`/transcriptions/${transcriptionId}`);
  return adaptTranscription(response.data);
};
