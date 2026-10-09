import api from "@/lib/api";
import { User, Media, Paginated, UserRole } from "@/types";

export interface SystemStats {
  total_users: number;
  active_users?: number;
  total_media: number;
  processing_media: number;
  failed_media?: number;
  completed_media?: number;
  success_rate?: number;
}

export interface SystemHealth {
  status: string;
  total_users: number;
  active_users: number;
  failed_media: number;
  failure_window_hours: number;
  processing_media: number;
  waiting_media: number;
  issues: string[];
  timestamp: string;
}

export interface MediaProcessingStats {
  total_media: number;
  uploaded: number;
  processing: number;
  completed: number;
  failed: number;
  success_rate: number;
  failure_rate: number;
  processing_rate: number;
}

export interface ProcessingTimeItem {
  task_type: string;
  model_name: string | null;
  runs: number;
  failures: number;
  avg_seconds: number | null;
  median_seconds: number | null;
  max_seconds: number | null;
  realtime_factor: number | null;
}

export interface ProcessingTimesResponse {
  days: number | null;
  items: ProcessingTimeItem[];
}

export interface GetPaginatedDataParams {
  page?: number;
  limit?: number;
  search?: string;
}

export type AdminMedia = Media & { owner_email?: string | null };

export interface QueueItem {
  position: number;
  media_id: string;
  filename: string | null;
  media_type: string;
  status: "uploaded" | "processing" | "analyzing";
  owner_email: string | null;
  created_at: string;
  stage_since: string;
  stage_seconds: number;
  stuck: boolean;
}

export interface ProcessingQueue {
  items: QueueItem[];
  counts: Record<string, number>;
  /** Tarefas esperando em cada fila do Celery; null se o Redis não respondeu. */
  broker: Record<string, number> | null;
  truncated: boolean;
}

export const getProcessingQueue = async (): Promise<ProcessingQueue> =>
  (await api.get<ProcessingQueue>("/admin/queue")).data;

export interface UserUpdatePayload {
  role?: UserRole;
}

export const getSystemStats = async (): Promise<SystemStats> => {
  const response = await api.get<SystemStats>("/admin/stats");
  return response.data;
};

export const getSystemHealth = async (): Promise<SystemHealth> => {
  const response = await api.get<SystemHealth>("/admin/stats/health");
  return response.data;
};

export const getProcessingTimes = async (days?: number): Promise<ProcessingTimesResponse> => {
  const response = await api.get<ProcessingTimesResponse>("/admin/stats/processing-times", {
    params: days ? { days } : {},
  });
  return response.data;
};

export const getMediaProcessingStats = async (): Promise<MediaProcessingStats> => {
  const response = await api.get<MediaProcessingStats>("/admin/stats/media-processing");
  return response.data;
};

export const getAllUsers = async ({ page = 1, limit = 10, search = '' }: GetPaginatedDataParams): Promise<Paginated<User>> => {
  const response = await api.get<Paginated<User>>("/admin/users", {
    params: { page, limit, search },
  });
  return response.data;
};

export const getAllMedia = async ({ page = 1, limit = 10, search = '' }: GetPaginatedDataParams): Promise<Paginated<AdminMedia>> => {
  const response = await api.get<Paginated<AdminMedia>>("/admin/media", {
    params: { page, limit, search },
  });
  return response.data;
};

export const setUserActive = async (userId: string, active: boolean): Promise<User> =>
  (await api.post<User>(`/admin/users/${userId}/${active ? "activate" : "deactivate"}`)).data;

export const deleteUser = async (userId: string): Promise<void> => {
  await api.delete(`/admin/users/${userId}`);
};

export const deleteMedia = async (mediaId: string): Promise<void> => {
  await api.delete(`/admin/media/${mediaId}`);
};

export const updateUser = async (userId: string, payload: UserUpdatePayload): Promise<User> => {
  const response = await api.put<User>(`/admin/users/${userId}`, payload);
  return response.data;
};

export const reprocessMedia = async (mediaId: string): Promise<{ message: string }> => {
  const response = await api.post(`/admin/media/${mediaId}/reprocess`);
  return response.data;
};

/** Resultado de um lote: o backend reprocessa até 50 mídias com falha por pedido. */
export interface BulkReprocessResult {
  reprocessed_count: number;
  failed_count: number;
  more_pending: boolean;
}

export const bulkReprocessFailedMedia = async (): Promise<BulkReprocessResult> => {
  const response = await api.post(`/admin/media/bulk-reprocess`);
  return response.data;
};

export const bulkReprocessMessage = (result: BulkReprocessResult): string => {
  const parts = [`${result.reprocessed_count} mídia(s) enviada(s) para reprocessamento.`];
  if (result.failed_count) parts.push(`${result.failed_count} não puderam ser reenviadas.`);
  if (result.more_pending) parts.push("Há mais mídias com falha: clique de novo para o próximo lote.");
  return parts.join(" ");
};

