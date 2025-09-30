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
}

export enum TranscriptionStatus {
  PENDING = "PENDING",
  PROCESSING = "PROCESSING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
}

// Represents a single segment of the transcription with timestamps
export interface TranscriptionSegment {
  id: number;
  start: number;
  end: number;
  text: string;
}

export interface Transcription {
  id: string;
  media_id: string;
  status: TranscriptionStatus;
  provider: string | null;
  created_at: string;
  processed_at: string | null;
  error_message: string | null;
  // The full transcription result, including segments with timestamps
  result: {
    text: string;
    segments: TranscriptionSegment[];
  } | null;
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
