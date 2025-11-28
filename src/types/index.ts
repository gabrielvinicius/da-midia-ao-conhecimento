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
  UPLOADED = "UPLOADED",
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
  sentiment_provider?: string;
  topic_modeling_provider?: string;
  processing_pipeline?: string[];
  file_size_mb?: number;
  error_message?: string;
  language?: string | null;
  filename?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  duration?: number | null;
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
  strategy?: string | null;
  bullet_points?: string[] | null;
  key_topics?: string[] | null;
  confidence_score?: number | null;
}

export interface SummarizationReprocessResponse {
  message: string;
  reprocessing: {
    media_id: string;
    provider: string;
    status: 'PROCESSING';
    task_id?: string;
  };
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
  transcription_id: string;
  label: string;
  score: number;
  confidence?: number | null;
  provider: string;
  model?: string | null;
  updated_at: string;
  full_result: Record<string, any>;
  created_at: string;
}

export interface SentimentAnalysisAck {
  transcription_id: string;
  provider: string;
  model?: string;
  status: 'PROCESSING';
  task_id?: string;
}

export interface SentimentAnalysisAcceptedResponse {
  message: string;
  analysis: SentimentAnalysisAck;
}

export enum TopicModelingStatus {
  PENDING = "PENDING",
  PROCESSING = "PROCESSING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
}

export interface TopicModelingResult {
  id: string;
  media_id: string;
  status: TopicModelingStatus;
  provider?: string | null;
  topics: string[]; // Array de strings conforme backend: ["Topic #1: tech, software", "Topic #2: design"]
  created_at: string;
  processed_at?: string | null;
  error_message?: string | null;
  raw_topics?: Record<string, any>[] | null;
  topic_summaries?: TopicSummaryDetail[] | null;
}

export interface TopicSummaryDetail {
  id: number | string;
  label: string;
  keywords: string[];
  summary_sentence?: string | null;
}

export interface TopicModelingAck {
  media_id?: string;
  provider: string;
  language: string;
  status: 'PROCESSING';
  task_id?: string;
}

export interface TopicModelingAcceptedResponse {
  message: string;
  analysis: TopicModelingAck;
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
