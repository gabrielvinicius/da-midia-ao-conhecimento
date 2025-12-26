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
  processing_media: number;
  issues: string[];
  timestamp: string;
}

export interface SuccessRateMetrics {
  completed: number;
  failed: number;
  total: number;
  success_rate: number;
}

export interface SystemPerformanceResponse {
  time_range: string;
  overall_health_score: number;
  success_rates: Record<string, SuccessRateMetrics>;
  user_metrics: Record<string, any>;
  media_distribution: Record<string, any>;
  recommendations: string[];
}

export interface ProcessingTrendsResponse {
  analysis_period_days: number;
  current_week: Record<string, any>;
  monthly_average: Record<string, any>;
  trend_direction: string;
  trend_percentage: number;
  insights: string[];
}

export interface MetricsSummaryResponse {
  provider_metrics: {
    available_metrics: string[];
    provider_type: string;
  };
  success_rates: Record<string, any>;
  user_metrics: Record<string, any>;
  media_distribution: Record<string, any>;
  business_kpis?: BusinessKPIsResponse;
  performance_summary?: PerformanceSummaryResponse;
  generated_at: string;
}

export interface BusinessKPIsResponse {
  total_uploads: number;
  successful_uploads: number;
  upload_success_rate_percent: number;
  total_revenue_usd: number;
  average_revenue_per_upload: number;
  processing_completions: number;
  calculated_at: string;
}

export interface PerformanceSummaryResponse {
  request_metrics: {
    total_requests: number;
    error_rate_percent: number;
    slow_requests?: number;
    error_requests?: number;
    slow_request_rate_percent?: number;
  };
  processing_metrics: {
    total_processing: number;
    completed: number;
    avg_transcription_seconds: number;
    avg_summarization_seconds: number;
  };
  resource_metrics: {
    cpu_usage_percent: number;
    memory_usage_percent: number;
  };
  throughput_metrics: {
    media_por_dia: number;
    conclusoes_por_hora: number;
    taxa_conclusao_percent: number;
  };
  overall_health: string;
  calculated_at: string;
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

export interface GetPaginatedDataParams {
  page?: number;
  limit?: number;
  search?: string;
}

export interface UserUpdatePayload {
  role?: UserRole;
}

export const getSystemStats = async (): Promise<SystemStats> => {
  const response = await api.get<SystemStats>("/admin/stats");
  return response.data;
};

export const getSystemPerformanceMetrics = async (timeRange: string = 'last_week'): Promise<SystemPerformanceResponse> => {
  const response = await api.get<SystemPerformanceResponse>("/monitoring/system-performance", {
    params: { time_range: timeRange },
  });
  return response.data;
};

export const getProcessingTrends = async (days: number = 30): Promise<ProcessingTrendsResponse> => {
  const response = await api.get<ProcessingTrendsResponse>("/monitoring/processing-trends", {
    params: { days },
  });
  return response.data;
};

export const getSystemHealth = async (): Promise<SystemHealth> => {
  const response = await api.get<SystemHealth>("/admin/stats/health");
  return response.data;
};

export const getMediaProcessingStats = async (): Promise<MediaProcessingStats> => {
  const response = await api.get<MediaProcessingStats>("/admin/stats/media-processing");
  return response.data;
};

export const getMetricsSummary = async (): Promise<MetricsSummaryResponse> => {
  const response = await api.get<MetricsSummaryResponse>("/monitoring/summary");
  return response.data;
};

export const getBusinessKpis = async (): Promise<BusinessKPIsResponse> => {
  const response = await api.get<BusinessKPIsResponse>("/monitoring/business/kpis");
  return response.data;
};

export const getAllUsers = async ({ page = 1, limit = 10, search = '' }: GetPaginatedDataParams): Promise<Paginated<User>> => {
  const response = await api.get<Paginated<User>>("/admin/users", {
    params: { page, limit, search },
  });
  return response.data;
};

export const getAllMedia = async ({ page = 1, limit = 10, search = '' }: GetPaginatedDataParams): Promise<Paginated<Media>> => {
  const response = await api.get<Paginated<Media>>("/admin/media", {
    params: { page, limit, search },
  });
  return response.data;
};

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

export const bulkReprocessFailedMedia = async (): Promise<{ message: string; reprocessed_count: number }> => {
  const response = await api.post(`/admin/media/bulk-reprocess`);
  return response.data;
};

export const cleanupOrphanedFiles = async (): Promise<{ message: string; cleaned_count: number }> => {
  const response = await api.post(`/admin/maintenance/cleanup-orphaned-files`);
  return response.data;
};
