// Chamadas HTTP da transcrição; os segmentos chegam como dicionários livres.
import api from "@/lib/api";
import { apiErrorStatus } from '@/lib/errors';
import { Transcription, TranscriptionSegment, TranscriptionStatus } from "@/types";

interface RawTranscriptionSegment {
  start?: number;
  end?: number;
  text?: string;
  speaker?: string | null;
  original_text?: string | null;
}

interface RawTranscriptionResponse {
  id: string;
  media_id: string;
  status: TranscriptionStatus;
  provider?: string | null;
  created_at: string;
  processed_at?: string | null;
  error_message?: string | null;
  text: string;
  language?: string | null;
  confidence_score?: number | null;
  segments?: RawTranscriptionSegment[] | null;
  speaker_aliases?: Record<string, string>;
  duration?: number | null;
  corrected_segments?: number;
}

const normalizeSegments = (segments: RawTranscriptionSegment[] = []): TranscriptionSegment[] =>
  segments.map((segment) => ({
    start: Number(segment.start ?? 0),
    end: Number(segment.end ?? 0),
    text: segment.text ?? "",
    speaker: segment.speaker ?? undefined,
    original_text: segment.original_text ?? undefined,
  }));

const adaptTranscription = (payload: RawTranscriptionResponse): Transcription => {
  const segments = normalizeSegments(payload.segments ?? []);
  return {
    id: payload.id,
    media_id: payload.media_id,
    status: payload.status,
    provider: payload.provider ?? null,
    created_at: payload.created_at,
    processed_at: payload.processed_at ?? null,
    error_message: payload.error_message ?? null,
    text: payload.text ?? "",
    language: payload.language ?? null,
    confidence_score: payload.confidence_score ?? null,
    segments,
    speaker_aliases: payload.speaker_aliases ?? {},
    duration: payload.duration ?? null,
    corrected_segments: payload.corrected_segments ?? 0,
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

/** Corrige o texto de um trecho; o texto do modelo fica guardado no backend. */
export const correctTranscriptionSegment = async (
  transcriptionId: string,
  index: number,
  text: string,
): Promise<Transcription> => {
  const response = await api.put<RawTranscriptionResponse>(
    `/transcriptions/${transcriptionId}/segments/${index}`,
    { text },
  );
  return adaptTranscription(response.data);
};
