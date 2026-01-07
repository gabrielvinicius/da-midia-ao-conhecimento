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
  return response.data;
};

export const getMediaByUser = async (
  page = 1,
  limit = 100,
  order: 'asc' | 'desc' = 'desc',
  search: string = "",
): Promise<PaginatedMedia> => {
  const response = await api.get<PaginatedMedia>('/media/', {
    params: {
      page,
      limit,
      order,
      search: search || undefined,
    },
  });

  return response.data;
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

export type AnalysisEstimation = {
  estimated_seconds: number;
  vram_gb: number;
  risk: 'safe' | 'warning' | 'dangerous' | 'terminal';
  recommendation: string;
};

export const getAnalysisEstimation = async (mediaId: string): Promise<AnalysisEstimation> => {
  const response = await api.get<AnalysisEstimation>(`/text-analysis/media/${mediaId}/estimate`);
  return response.data;
};

export type SystemStatusResponse = {
  pressure: 'low' | 'moderate' | 'high' | 'critical';
  cpu_usage: number;
  ram_usage: number;
  gpu_vram_usage: number | null;
};

export const getSystemStatus = async (): Promise<SystemStatusResponse> => {
  const response = await api.get<SystemStatusResponse>('/monitoring/system-status');
  return response.data;
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
