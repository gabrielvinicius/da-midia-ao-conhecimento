// Queries API - Para operações de leitura (CQRS Read Side)
import api from '@/lib/api';
import { 
  Media, 
  User, 
  Transcription, 
  Summary, 
  SentimentAnalysisResult, 
  TopicModelingResult, 
  SystemStats, 
  UserResponse, 
  Notification 
} from '@/types';

// =============================================================================
// MEDIA QUERIES
// =============================================================================

export const getMediaById = async (mediaId: string): Promise<Media> => {
  console.log('📖 Executando GetMediaByIdQuery:', mediaId);
  
  const response = await api.get<Media>(`/media/${mediaId}`);
  
  console.log('✅ GetMediaByIdQuery executada:', response.data);
  return response.data;
};

export const getMediaByUser = async (): Promise<Media[]> => {
  console.log('📖 Executando GetMediaByUserQuery');
  
  const response = await api.get<Media[]>('/media/');
  
  console.log('✅ GetMediaByUserQuery executada:', response.data.length, 'items');
  return response.data;
};

// =============================================================================
// TRANSCRIPTION QUERIES
// =============================================================================

export const getTranscriptionByMediaId = async (mediaId: string): Promise<Transcription> => {
  console.log('📖 Executando GetTranscriptionByMediaIdQuery:', mediaId);
  
  const response = await api.get<Transcription>(`/transcriptions/?media_id=${mediaId}`);
  
  console.log('✅ GetTranscriptionByMediaIdQuery executada:', response.data);
  return response.data;
};

export const getTranscriptionById = async (transcriptionId: string): Promise<Transcription> => {
  console.log('📖 Executando GetTranscriptionByIdQuery:', transcriptionId);
  
  const response = await api.get<Transcription>(`/transcriptions/${transcriptionId}`);
  
  console.log('✅ GetTranscriptionByIdQuery executada:', response.data);
  return response.data;
};

// =============================================================================
// SUMMARIZATION QUERIES
// =============================================================================

export const getSummaryByMediaId = async (mediaId: string): Promise<Summary> => {
  console.log('📖 Executando GetSummaryByMediaIdQuery:', mediaId);
  
  const response = await api.get<Summary>(`/summaries/?media_id=${mediaId}`);
  
  console.log('✅ GetSummaryByMediaIdQuery executada:', response.data);
  return response.data;
};

export const getSummaryById = async (summaryId: string): Promise<Summary> => {
  console.log('📖 Executando GetSummaryByIdQuery:', summaryId);
  
  const response = await api.get<Summary>(`/summaries/${summaryId}`);
  
  console.log('✅ GetSummaryByIdQuery executada:', response.data);
  return response.data;
};

// =============================================================================
// SENTIMENT ANALYSIS QUERIES
// =============================================================================

export const getSentimentAnalysisByMediaId = async (mediaId: string): Promise<SentimentAnalysisResult | null> => {
  console.log('📖 Executando GetSentimentAnalysisByMediaIdQuery:', mediaId);
  
  try {
    const response = await api.get<SentimentAnalysisResult>(`/sentiment-analysis/?media_id=${mediaId}`);
    console.log('✅ GetSentimentAnalysisByMediaIdQuery executada:', response.data);
    return response.data;
  } catch (error: any) {
    if (error?.response?.status === 404) {
      return null;
    }
    throw error;
  }
};

// =============================================================================
// TOPIC MODELING QUERIES
// =============================================================================

export const getTopicModelingByMediaId = async (mediaId: string): Promise<TopicModelingResult | null> => {
  console.log('📖 Executando GetTopicModelingByMediaIdQuery:', mediaId);
  try {
    const response = await api.get<TopicModelingResult>(`/topic-modeling/?media_id=${mediaId}`);
    console.log('✅ GetTopicModelingByMediaIdQuery executada:', response.data);
    return response.data;
  } catch (error: any) {
    if (error?.response?.status === 404) {
      return null;
    }
    throw error;
  }
};

// =============================================================================
// AUTH QUERIES
// =============================================================================

export const getCurrentUser = async (): Promise<User> => {
  console.log('📖 Executando GetCurrentUserQuery');
  
  const response = await api.get<User>('/auth/me');
  
  console.log('✅ GetCurrentUserQuery executada:', response.data);
  return response.data;
};

// =============================================================================
// PROVIDER QUERIES
// =============================================================================

export const getStorageProviders = async (): Promise<string[]> => {
  console.log('📖 Executando GetStorageProvidersQuery');
  
  const response = await api.get<string[]>('/providers/storage');
  
  console.log('✅ GetStorageProvidersQuery executada:', response.data);
  return response.data;
};

export const getTranscriptionProviders = async (): Promise<string[]> => {
  console.log('📖 Executando GetTranscriptionProvidersQuery');
  
  const response = await api.get<string[]>('/providers/transcription');
  
  console.log('✅ GetTranscriptionProvidersQuery executada:', response.data);
  return response.data;
};

export const getSummarizationProviders = async (): Promise<string[]> => {
  console.log('📖 Executando GetSummarizationProvidersQuery');
  
  const response = await api.get<string[]>('/providers/summarization');
  
  console.log('✅ GetSummarizationProvidersQuery executada:', response.data);
  return response.data;
};

export const getSentimentProviders = async (): Promise<string[]> => {
  console.log('📖 Executando GetSentimentProvidersQuery');
  const response = await api.get<string[]>('/providers/sentiment');
  console.log('✅ GetSentimentProvidersQuery executada:', response.data);
  return response.data;
};

export const getTopicModelingProviders = async (): Promise<string[]> => {
  console.log('📖 Executando GetTopicModelingProvidersQuery');
  const response = await api.get<string[]>('/providers/topics');
  console.log('✅ GetTopicModelingProvidersQuery executada:', response.data);
  return response.data;
};

export const getAllProviders = async (): Promise<Record<string, string[]>> => {
  console.log('📖 Executando GetAllProvidersQuery');
  
  const response = await api.get<Record<string, string[]>>('/providers/');
  
  console.log('✅ GetAllProvidersQuery executada:', response.data);
  return response.data;
};

// =============================================================================
// NOTIFICATION QUERIES
// =============================================================================

export const getNotifications = async (): Promise<Notification[]> => {
  console.log('📖 Executando GetNotificationsQuery');
  
  const response = await api.get<Notification[]>('/notifications/');
  
  console.log('✅ GetNotificationsQuery executada:', response.data.length, 'notifications');
  return response.data;
};

// =============================================================================
// ADMIN QUERIES
// =============================================================================

export const getSystemStats = async (): Promise<SystemStats> => {
  console.log('📖 Executando GetSystemStatsQuery');
  
  const response = await api.get<SystemStats>('/admin/stats');
  
  console.log('✅ GetSystemStatsQuery executada:', response.data);
  return response.data;
};

export const getAllUsers = async (): Promise<UserResponse[]> => {
  console.log('📖 Executando GetAllUsersQuery');
  
  const response = await api.get<UserResponse[]>('/admin/users');
  
  console.log('✅ GetAllUsersQuery executada:', response.data.length, 'users');
  return response.data;
};

export const getAllMediaAdmin = async (): Promise<Media[]> => {
  console.log('📖 Executando GetAllMediaAdminQuery');
  
  const response = await api.get<Media[]>('/admin/media');
  
  console.log('✅ GetAllMediaAdminQuery executada:', response.data.length, 'media items');
  return response.data;
};
