export enum UserRole {
  USER = "USER",
  ADMIN = "ADMIN",
}

export interface User {
  id: string;
  email: string;
  role: UserRole;
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
  PENDING = "PENDING",
  PROCESSING = "PROCESSING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
}

export interface Media {
  id: string;
  user_id: string;
  original_file_path: string;
  media_type: MediaType;
  status: MediaStatus;
  created_at: string;
  storage_provider?: string;
  transcription_provider?: string;
  summarization_provider?: string;
  processing_pipeline?: string[];
  file_size_mb?: number;
  error_message?: string;
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

export interface TranscriptionResult {
  text: string;
  segments: TranscriptionSegment[];
  diarized?: boolean;
  [key: string]: any; // Para campos adicionais do provider
}

export interface Transcription {
  id: string;
  media_id: string;
  status: TranscriptionStatus;
  provider: string | null;
  created_at: string;
  processed_at: string | null;
  error_message: string | null;
  result: TranscriptionResult | null;
  speaker_aliases?: Record<string, string>;
  
  // Legacy support - para compatibilidade com código antigo
  text?: string; // Deprecated: usar result.text
}

export enum SummaryStatus {
  PENDING = "PENDING",
  PROCESSING = "PROCESSING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
}

export interface Summary {
  id: string;
  media_id: string;
  status: SummaryStatus;
  provider: string | null;
  text: string | null;
  created_at: string;
  processed_at: string | null;
  error_message: string | null;
}

export interface Notification {
  id: string;
  user_id: string;
  content: string;
  read: boolean;
  created_at: string;
}

export interface PaginatedResponse<T> {
  total_items: number;
  total_pages: number;
  current_page: number;
  items: T[];
}

// --- V2: Analysis Types ---

export enum AnalysisType {
  SENTIMENT = "SENTIMENT",
  TOPIC_MODELING = "TOPIC_MODELING",
}

// A generic Analysis result type
export interface AnalysisResult {
  [key: string]: any;
}

export interface Analysis {
  id: string;
  media_id: string;
  type: AnalysisType;
  result: AnalysisResult;
  label?: string;
  score?: number;
}

// Specific analysis result types baseados no backend
export interface SentimentAnalysisResult {
  id: string;
  media_id: string;
  label: string;
  score: number;
  full_result: Record<string, any>;
  created_at: string;
}

export interface TopicModelingResult {
  id: string;
  media_id: string;
  topics: string[]; // Array de strings conforme backend: ["Topic #1: tech, software", "Topic #2: design"]
  created_at: string;
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
  created_at: string;
}

export interface UserUpdateRequest {
  role?: UserRole;
}
