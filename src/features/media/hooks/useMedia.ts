// MIGRATED TO CQRS PATTERN
// @see /src/hooks/useQueries.ts for read operations
// @see /src/hooks/useCommands.ts for write operations

import { 
  useMediaByUserQuery,
  useMediaByIdQuery,
} from '@/hooks/useQueries';
import {
  useCreateMediaCommand,
  useReprocessMediaCommand,
} from '@/hooks/useCommands';

// Re-export legacy hooks with deprecation warnings
import { UploadMediaParams } from '../api';

// =============================================================================
// LEGACY HOOKS - Use CQRS hooks instead
// =============================================================================

/**
 * @deprecated Use useMediaByUserQuery() instead
 */
export const useMediaList = () => {
  console.warn('⚠️ useMediaList() is deprecated. Use useMediaByUserQuery() instead.');
  return useMediaByUserQuery();
};

/**
 * @deprecated Use useMediaByIdQuery() instead
 */
export const useMediaDetail = (id: string) => {
  console.warn('⚠️ useMediaDetail() is deprecated. Use useMediaByIdQuery() instead.');
  return useMediaByIdQuery(id);
};

/**
 * @deprecated Use useCreateMediaCommand() instead
 */
export const useUploadMedia = () => {
  console.warn('⚠️ useUploadMedia() is deprecated. Use useCreateMediaCommand() instead.');
  return useCreateMediaCommand();
};

/**
 * @deprecated Use useReprocessMediaCommand() instead
 */
export const useReprocessMedia = () => {
  console.warn('⚠️ useReprocessMedia() is deprecated. Use useReprocessMediaCommand() instead.');
  return useReprocessMediaCommand();
};

// =============================================================================
// MODERN CQRS EXPORTS
// =============================================================================

// Export modern CQRS hooks for convenience
export {
  useMediaByUserQuery as useMediaListQuery,
  useMediaByIdQuery as useMediaDetailQuery,
  useMediaDetailQuery as useCompleteMediaQuery, // Includes all related data
} from '@/hooks/useQueries';

export {
  useCreateMediaCommand as useUploadMediaCommand,
  useReprocessMediaCommand,
} from '@/hooks/useCommands';
