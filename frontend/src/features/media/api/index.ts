// Chamadas HTTP das mídias: listagem, detalhe, envio, reprocessamento e exclusão.
import { isAxiosError } from 'axios';

import api from '@/lib/api';
import { Media, MediaStatus, PaginatedMedia } from '@/types';

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
  onProgress?: (percent: number) => void;
};

export const getMedia = async (mediaId: string): Promise<Media> =>
  (await api.get<Media>(`/media/${mediaId}`)).data;

export const listMedia = async (
  page = 1,
  limit = 100,
  order: 'asc' | 'desc' = 'desc',
  search = '',
  statuses: MediaStatus[] = [],
): Promise<PaginatedMedia> =>
  (await api.get<PaginatedMedia>('/media/', {
    params: { page, limit, order, search: search || undefined, status: statuses.length ? statuses : undefined },
    // status=a&status=b, como o FastAPI lê listas (o padrão do axios é status[]=).
    paramsSerializer: { indexes: null },
  })).data;

export const getMediaStats = async (): Promise<MediaStatsResponse> =>
  (await api.get<MediaStatsResponse>('/media/stats')).data;

/** Opções do pipeline oferecidas no envio (armazenamento, transcrição). */
export const getProviders = async (): Promise<ProvidersResponse> =>
  (await api.get<ProvidersResponse>('/providers')).data;

export const getAnalysisEstimation = async (mediaId: string): Promise<AnalysisEstimation> =>
  (await api.get<AnalysisEstimation>(`/transcriptions/media/${mediaId}/estimate`)).data;

// Envio em partes: a Cloudflare recusa requisições acima de 100 MB. Cada
// parte vai a partir do total já recebido pelo servidor; uma parte que falha
// é repetida do ponto que ele confirmar.
export const UPLOAD_PART_BYTES = 32 * 1024 * 1024;
const PART_ATTEMPTS = 4;

type UploadState = { upload_id: string; offset: number; size_bytes: number; part_max_bytes: number };

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Erro que outra tentativa não resolve (arquivo recusado, sessão expirada). */
const isFinal = (error: unknown) => {
  const status = isAxiosError(error) ? error.response?.status : undefined;
  return status !== undefined && status < 500 && status !== 409 && status !== 408 && status !== 429;
};

const sendPart = async (
  uploadId: string,
  file: File,
  offset: number,
  partBytes: number,
  onLoaded: (loaded: number) => void,
): Promise<number> => {
  for (let attempt = 1; ; attempt++) {
    try {
      const { data } = await api.put<UploadState>(`/media/uploads/${uploadId}`, file.slice(offset, offset + partBytes), {
        params: { offset },
        headers: { 'Content-Type': 'application/octet-stream' },
        timeout: 300000,
        onUploadProgress: (event) => onLoaded(event.loaded),
      });
      return data.offset;
    } catch (error) {
      if (attempt >= PART_ATTEMPTS || isFinal(error)) throw error;
      await wait(1000 * attempt);
      // O servidor diz de onde continuar (a parte pode ter chegado em parte).
      offset = (await api.get<UploadState>(`/media/uploads/${uploadId}`)).data.offset;
      onLoaded(0);
    }
  }
};

export const uploadMedia = async (
  { file, storageProvider, transcriptionProvider }: UploadMediaRequest,
  options?: UploadOptions,
): Promise<Media> => {
  const { data: started } = await api.post<UploadState>('/media/uploads', {
    filename: file.name,
    size_bytes: file.size,
    storage_provider: storageProvider || 'local',
    transcription_provider: transcriptionProvider || null,
  });
  const partBytes = Math.min(UPLOAD_PART_BYTES, started.part_max_bytes);
  try {
    let offset = 0;
    while (offset < file.size) {
      const base = offset;
      offset = await sendPart(started.upload_id, file, offset, partBytes, (loaded) => {
        const sent = Math.min(file.size, base + loaded);
        options?.onProgress?.(Math.round((sent * 100) / file.size));
      });
    }
    return (await api.post<Media>(`/media/uploads/${started.upload_id}/complete`, null, { timeout: 300000 })).data;
  } catch (error) {
    // Libera o espaço no servidor; se nem isso der, o envio expira sozinho.
    api.delete(`/media/uploads/${started.upload_id}`).catch(() => undefined);
    throw error;
  }
};

export type UrlImportOptions = { enabled: boolean; max_minutes: number };

/** Se o servidor aceita links do YouTube (pode estar desligado). */
export const getUrlImportOptions = async (): Promise<UrlImportOptions> =>
  (await api.get<UrlImportOptions>('/media/import')).data;

/** O servidor baixa o vídeo e o registra como um envio comum. */
export const importMediaFromUrl = async (
  url: string,
  storageProvider: string,
  transcriptionProvider?: string,
): Promise<Media> =>
  (
    await api.post<Media>(
      '/media/import',
      { url, storage_provider: storageProvider, transcription_provider: transcriptionProvider || null },
      { timeout: 15 * 60 * 1000 }, // o download pode levar minutos
    )
  ).data;

export const reprocessMedia = async (mediaId: string): Promise<{ message: string }> =>
  (await api.post<{ message: string }>(`/media/${mediaId}/reprocess`)).data;

export const deleteMedia = async (mediaId: string): Promise<void> => {
  await api.delete(`/media/${mediaId}`);
};
