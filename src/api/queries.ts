// Queries API - Para operações de leitura (CQRS Read Side)
import api from '@/lib/api';
import {
  Media,
  User,
  Transcription,
  TextAnalysisResponse,
  SystemStats,
  UserResponse,
  Paginated,
  PaginatedMedia,
  MediaType,
  MediaStatus,
} from '@/types';

export type ProviderOption = {
  name: string;
  label: string;
  description?: string | null;
  capabilities?: Record<string, any>;
};

export type ProvidersResponse = {
  stages: Record<string, ProviderOption[]>;
};

type RawTranscription = Partial<Transcription> & {
  content?: string | null;
};

const normalizeMediaShape = (payload: any): Media => {
  const media_type = String(payload.media_type || payload.mediaType || '').toUpperCase() as MediaType;
  const status = String(payload.status || '').toUpperCase() as MediaStatus;
  return {
    id: String(payload.id),
    filename: payload.filename ?? null,
    content_type: payload.mime_type ?? payload.content_type ?? null,
    size: payload.file_size ?? payload.size ?? null,
    media_type,
    status,
    created_at: String(payload.created_at),
    error_message: payload.error_message ?? null,
    language: payload.language ?? null,
    duration: payload.duration ?? null,
    original_file_path: payload.original_file_path ?? null,
    storage_provider: payload.storage_provider ?? null,
    transcription_provider: payload.transcription_provider ?? null,
    summarization_provider: payload.summarization_provider ?? null,
    sentiment_provider: payload.sentiment_provider ?? null,
    topic_modeling_provider: payload.topic_modeling_provider ?? null,
  } as Media;
};

const normalizeTranscription = (payload: RawTranscription): Transcription => {
  const segments = Array.isArray(payload.segments) ? payload.segments : [];
  return {
    id: String(payload.id),
    media_id: String(payload.media_id),
    status: payload.status as any,
    provider: payload.provider ?? null,
    created_at: String(payload.created_at),
    processed_at: (payload.processed_at as any) ?? null,
    error_message: (payload.error_message as any) ?? null,
    text: String((payload as any).text ?? payload.content ?? ""),
    segments,
    speaker_aliases: (payload as any).speaker_aliases ?? {},
    language: (payload as any).language ?? null,
    confidence_score: (payload as any).confidence_score ?? null,
  };
};

// =============================================================================
// MEDIA QUERIES
// =============================================================================

export const getMediaById = async (mediaId: string): Promise<Media> => {
  const response = await api.get<Media>(`/media/${mediaId}`);
  return normalizeMediaShape(response.data);
};

export const getMediaByUser = async (
  page = 1,
  limit = 100, // API permite até 100
  order: 'asc' | 'desc' = 'desc',
  search: string = "",
): Promise<PaginatedMedia> => {
  const response = await api.get<Partial<Paginated<Media>>>('/media/', {
    params: {
      page,
      limit,
      order,
      search: search || undefined,
    },
  });

  const items = Array.isArray(response.data?.items)
    ? response.data.items.map(normalizeMediaShape)
    : [];
  const total = typeof response.data?.total === 'number' ? response.data.total : items.length;
  const resolvedLimit = response.data?.limit ?? limit;
  const resolvedPage = response.data?.page ?? page;
  const resolvedPages = response.data?.pages ?? Math.max(1, Math.ceil(total / resolvedLimit));

  return {
    items,
    total,
    page: resolvedPage,
    pages: resolvedPages,
    limit: resolvedLimit,
  };
};

// Estatísticas das mídias do usuário atual
export type MediaStatsResponse = {
  total: number;
  by_status: Record<string, number>;
};

export const getMediaStats = async (): Promise<MediaStatsResponse> => {
  const response = await api.get<MediaStatsResponse>('/media/stats');
  return response.data;
};

// =============================================================================
// TRANSCRIPTION QUERIES
// =============================================================================

export const getTranscriptionByMediaId = async (mediaId: string): Promise<Transcription> => {
  const response = await api.get<RawTranscription>(`/transcriptions/?media_id=${mediaId}`);
  const transcription = normalizeTranscription(response.data);
  return transcription;
};

export const getTranscriptionById = async (transcriptionId: string): Promise<Transcription> => {
  const response = await api.get<RawTranscription>(`/transcriptions/${transcriptionId}`);
  const transcription = normalizeTranscription(response.data);
  return transcription;
};

// =============================================================================
// TEXT ANALYSIS QUERIES (unificado)
// =============================================================================

export const getTextAnalysisByMediaId = async (mediaId: string): Promise<TextAnalysisResponse | null> => {
  try {
    const response = await api.get<TextAnalysisResponse>(`/text-analysis/media/${mediaId}`);
    return response.data;
  } catch (error: any) {
    if (error?.response?.status === 404) {
      return null;
    }
    throw error;
  }
};

// =============================================================================
// AUTH QUERIES
// =============================================================================

export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get<User>('/auth/me');
  return response.data;
};

// =============================================================================
// PROVIDERS (pipeline)
// =============================================================================

export const getProviders = async (): Promise<ProvidersResponse> => {
  const response = await api.get<ProvidersResponse>("/providers");
  return response.data;
};

// Notas:
// - O frontend consulta `GET /providers` para listar opções selecionáveis do pipeline no upload.
// - Notificações são entregues via WebSocket no frontend atual; leitura por API é opcional no backend.

// =============================================================================
// ADMIN QUERIES
// =============================================================================

export const getSystemStats = async (): Promise<SystemStats> => {
  const response = await api.get<SystemStats>('/admin/stats');
  return response.data;
};

export const getAllUsers = async (): Promise<Paginated<UserResponse>> => {
  const response = await api.get<Paginated<UserResponse>>('/admin/users');
  return response.data;
};

export const getAllMediaAdmin = async (): Promise<Paginated<Media>> => {
  const response = await api.get<Paginated<Media>>('/admin/media');
  return response.data;
};
