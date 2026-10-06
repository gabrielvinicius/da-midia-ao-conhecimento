// Chamadas HTTP das mídias: listagem, detalhe, envio, reprocessamento e exclusão.
import type { AxiosProgressEvent } from 'axios';

import api from '@/lib/api';
import { Media, PaginatedMedia } from '@/types';

export type ProviderOption = {
  name: string;
  label: string;
  description?: string | null;
  capabilities?: Record<string, unknown>;
};

export type ProvidersResponse = {
  stages: Record<string, ProviderOption[]>;
};

/** Contagens das mídias do usuário; as chaves de `by_type` vêm em minúsculas. */
export type MediaStatsResponse = {
  total: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
};

// Tempo estimado do processamento completo, calculado pela duração da
// gravação e pela velocidade medida nos processamentos anteriores. Nulo
// enquanto não há base para estimar (duração ainda não lida, sem histórico).
export type AnalysisEstimation = {
  estimated_seconds: number | null;
  media_seconds: number | null;
  includes_analysis: boolean;
};

export interface UploadMediaRequest {
  file: File;
  storageProvider: string;
  transcriptionProvider?: string;
}

type UploadOptions = {
  onProgress?: (percent: number, event: AxiosProgressEvent) => void;
};

export const getMedia = async (mediaId: string): Promise<Media> =>
  (await api.get<Media>(`/media/${mediaId}`)).data;

export const listMedia = async (
  page = 1,
  limit = 100,
  order: 'asc' | 'desc' = 'desc',
  search = '',
): Promise<PaginatedMedia> =>
  (await api.get<PaginatedMedia>('/media/', {
    params: { page, limit, order, search: search || undefined },
  })).data;

export const getMediaStats = async (): Promise<MediaStatsResponse> =>
  (await api.get<MediaStatsResponse>('/media/stats')).data;

/** Opções do pipeline oferecidas no envio (armazenamento, transcrição). */
export const getProviders = async (): Promise<ProvidersResponse> =>
  (await api.get<ProvidersResponse>('/providers')).data;

export const getAnalysisEstimation = async (mediaId: string): Promise<AnalysisEstimation> =>
  (await api.get<AnalysisEstimation>(`/transcriptions/media/${mediaId}/estimate`)).data;

export const uploadMedia = async (
  { file, storageProvider, transcriptionProvider }: UploadMediaRequest,
  options?: UploadOptions,
): Promise<Media> => {
  const formData = new FormData();
  formData.append('file', file, file.name);
  const response = await api.post<Media>('/media/', formData, {
    params: {
      storage_provider: storageProvider || undefined,
      transcription_provider: transcriptionProvider || undefined,
    },
    timeout: 300000, // 5 minutos
    onUploadProgress: (event) => {
      const percent = event.total ? Math.round((event.loaded * 100) / event.total) : 0;
      options?.onProgress?.(percent, event);
    },
  });
  return response.data;
};

export const reprocessMedia = async (mediaId: string): Promise<{ message: string }> =>
  (await api.post<{ message: string }>(`/media/${mediaId}/reprocess`)).data;

export const deleteMedia = async (mediaId: string): Promise<void> => {
  await api.delete(`/media/${mediaId}`);
};
