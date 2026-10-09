export enum UserRole {
  USER = "USER",
  ADMIN = "ADMIN",
}

/** Administrador: o papel vem da API exatamente como "ADMIN". */
export const isAdminUser = (user?: { role?: UserRole | string } | null): boolean => user?.role === UserRole.ADMIN;

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
  VIDEO = "video",
  AUDIO = "audio",
  TEXT = "text",
}

export enum MediaStatus {
  UPLOADED = "uploaded",
  PENDING = "pending", // Deprecated: Backend uses UPLOADED
  PROCESSING = "processing", // transcrição ou extração do texto
  ANALYZING = "analyzing", // texto pronto, análise em andamento
  COMPLETED = "completed", // análise concluída
  FAILED = "failed",
}

/** Mídia com trabalho em andamento: transcrição/extração ou análise. */
export const isInProgress = (status?: MediaStatus | string | null): boolean =>
  status === MediaStatus.PROCESSING || status === MediaStatus.ANALYZING;

// Aligned with Backend DTO (MediaResponse)
export interface Media {
  id: string;
  user_id: string;
  filename: string | null;
  content_type: string | null;
  size: number | null;
  media_type: MediaType;
  status: MediaStatus;
  created_at: string;
  
  // Optional fields
  error_message?: string | null;
  language?: string | null;
  duration?: number | null;
  storage_provider?: string | null;
  transcription_provider?: string | null;
}

export enum TranscriptionStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
}

export interface TranscriptionSegment {
  id?: number;
  start: number;
  end: number;
  text: string;
  speaker?: string;
  /** Texto do modelo, quando o usuário corrigiu o trecho. */
  original_text?: string;
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
  /** Duração lida do arquivo; a fala pode terminar antes. */
  duration?: number | null;
  corrected_segments?: number;
}

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  content: string;
  priority: string;
  status: string;
  created_at: string;
  read: boolean;
  variables?: Record<string, unknown>;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

// Paginação simplificada (API /media)
export type PaginatedMedia = Paginated<Media>;

// --- Text Analysis (unificado) ---

interface TextAnalysisSentimentItem {
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
  representative_snippets: string[];
  size: number;
  /** Momento em que o tema aparece pela primeira vez (gravações). */
  start?: number | null;
  /** Título dado pela IA, quando o usuário o corrigiu. */
  original_title?: string | null;
}

export interface TextAnalysisResponse {
  analysis_id: string;
  document_id: string;
  overall_sentiment: string;
  sentiment_items: TextAnalysisSentimentItem[];
  topics: TextAnalysisTopic[];
  diagnostics: Record<string, unknown>;
  media_id?: string | null;
  transcription_id?: string | null;
  provider?: string | null;
  user_id?: string | null;
  summary?: string | null;
}
