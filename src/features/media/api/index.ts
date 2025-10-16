// DEPRECATED: Use CQRS hooks instead
// @see /src/hooks/useQueries.ts for read operations
// @see /src/hooks/useCommands.ts for write operations

import { 
  getMediaById as queryGetMediaById,
  getMediaByUser as queryGetMediaByUser,
} from '@/api/queries';
import {
  executeCreateMedia,
  executeReprocessMedia,
  CreateMediaCommand,
  ReprocessMediaCommand,
} from '@/api/commands';
import { Media } from '@/types';

export interface UploadMediaParams {
  file: File;
  storageProvider: string;
  transcriptionProvider?: string;
  summarizationProvider?: string;
}

// =============================================================================
// LEGACY SUPPORT - Use CQRS hooks instead
// =============================================================================

/**
 * @deprecated Use useMediaByUserQuery() hook instead
 */
export const listMedia = async (): Promise<Media[]> => {
  console.warn('⚠️ listMedia() is deprecated. Use useMediaByUserQuery() hook instead.');
  return queryGetMediaByUser();
};

/**
 * @deprecated Use useMediaByIdQuery() hook instead
 */
export const getMediaById = async (id: string): Promise<Media> => {
  console.warn('⚠️ getMediaById() is deprecated. Use useMediaByIdQuery() hook instead.');
  return queryGetMediaById(id);
};

/**
 * @deprecated Use useCreateMediaCommand() hook instead
 */
export const uploadMedia = async (params: UploadMediaParams): Promise<Media> => {
  console.warn('⚠️ uploadMedia() is deprecated. Use useCreateMediaCommand() hook instead.');
  
  const command: CreateMediaCommand = {
    file: params.file,
    storageProvider: params.storageProvider,
    transcriptionProvider: params.transcriptionProvider,
    summarizationProvider: params.summarizationProvider,
  };
  
  return executeCreateMedia(command);
};

/**
 * @deprecated Use useReprocessMediaCommand() hook instead
 */
export const reprocessMedia = async (mediaId: string): Promise<{ message: string }> => {
  console.warn('⚠️ reprocessMedia() is deprecated. Use useReprocessMediaCommand() hook instead.');
  
  const command: ReprocessMediaCommand = { mediaId };
  return executeReprocessMedia(command);
};
