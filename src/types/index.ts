export enum UserRole {
  USER = "USER",
  ADMIN = "ADMIN",
}

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at?: string;
}

export interface UserRegistration {
  email: string;
  password: string;
}

export interface UserCredentials {
  email: string;
  password: string;
}

export interface ChangePasswordPayload {
  old_password: string;
  new_password: string;
}

export enum MediaType {
  VIDEO = "VIDEO",
  AUDIO = "AUDIO",
  TEXT = "TEXT",
}

export enum MediaStatus {
  UPLOADED = "UPLOADED",
  PENDING = "PENDING",
  PROCESSING = "PROCESSING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
}

// Aligned with Backend DTO (MediaResponse)
export interface Media {
  id: string;
  filename: string | null;
  content_type: string | null;
  size: number | null;
  media_type: MediaType;
  status: MediaStatus;
  created_at: string;
  
  // Optional fields that might be present depending on context
  error_message?: string;
  language?: string | null;
  duration?: number | null;

  // Campos estendidos (podem não estar presentes em todas as rotas)
  original_file_path?: string | null;
  storage_provider?: string | null;
  transcription_provider?: string | null;
  summarization_provider?: string | null;
  sentiment_provider?: string | null;
  topic_modeling_provider?: string | null;
  processing_pipeline?: string[] | null;
  file_size_mb?: number | null;
}

// Legacy Video interface for backward compatibility
export interface Video extends Media {
  title?: string;
  duration?: number;
}

export enum TranscriptionStatus {
  PENDING = "PENDING",
  PROCESSING = "PROCESSING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
}

export interface TranscriptionSegment {
  id?: number;
  start: number;
  end: number;
  text: string;
  speaker?: string;
}

// Alinhado com o backend (TranscriptionResponse)
export interface Transcription {
  id: string;
  media_id: string;
  status: TranscriptionStatus;
  provider: string | null;
  created_at: string;
  processed_at: string | null;
  error_message: string | null;
  text: string;
  segments: TranscriptionSegment[];
  speaker_aliases: Record<string, string>;
  language?: string | null;
  confidence_score?: number | null;
}

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  content: string;
  status: string;
  priority: string;
  created_at: string;
  sent_at: string | null;
  error_message: string | null;
  read?: boolean;
  delivered_at?: string | null;
  opened_at?: string | null;
  template_name?: string | null;
  variables?: Record<string, unknown>;
  retries?: number;
  max_retries?: number;
  updated_at?: string | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

// Alias legado para compatibilidade (preferir Paginated<T>)
export type PaginatedResponse<T> = Paginated<T>;

// Paginação simplificada (API /media)
export type PaginatedMedia = Paginated<Media>;

// --- Text Analysis (unificado) ---

export interface TextAnalysisSentimentItem {
  chunk_id: string;
  label: string;
  score: number;
  text: string;
  start?: number | null;
  end?: number | null;
}

export interface TextAnalysisTopic {
  topic_id: number;
  title?: string | null;
  keywords: string[];
  summary_md?: string | null;
  representative_snippets: string[];
  size: number;
  diagnostics: Record<string, any>;
}

export interface TextAnalysisResponse {
  analysis_id: string;
  document_id: string;
  overall_sentiment: string;
  sentiment_items: TextAnalysisSentimentItem[];
  topics: TextAnalysisTopic[];
  diagnostics: Record<string, any>;
  media_id?: string | null;
  transcription_id?: string | null;
  provider?: string | null;
  user_id?: string | null;
}

// Admin types
export interface SystemStats {
  total_users: number;
  total_media: number;
  total_transcriptions: number;
  total_summaries: number;
  active_tasks: number;
  system_uptime: string;
  database_status: string;
  redis_status: string;
}

export interface UserResponse {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at?: string;
}

export interface UserUpdateRequest {
  role?: UserRole;
  is_active?: boolean;
}
