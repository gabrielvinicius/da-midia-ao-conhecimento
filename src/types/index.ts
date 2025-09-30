
export interface User {
  id: string;
  email: string;
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

export interface Transcription {
  id: string;
  media_id: string;
  text: string | null;
  status: TranscriptionStatus;
  provider: string | null;
  created_at: string;
  processed_at: string | null;
  error_message: string | null;
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
