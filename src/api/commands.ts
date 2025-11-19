// Commands API - Para operações de escrita (CQRS Write Side)
import type { AxiosProgressEvent } from 'axios';

import api from '@/lib/api';
import authService from '@/services/auth.service';
import { Media, UserUpdateRequest } from '@/types';

// =============================================================================
// MEDIA COMMANDS
// =============================================================================

export interface CreateMediaCommand {
  file: File;
  storageProvider: string;
  transcriptionProvider?: string;
  summarizationProvider?: string;
  sentimentProvider?: string;
  topicModelingProvider?: string;
}

export interface ReprocessMediaCommand {
  mediaId: string;
}

type UploadOptions = {
  onProgress?: (percent: number, event: AxiosProgressEvent) => void;
};

export const executeCreateMedia = async (
  command: CreateMediaCommand,
  options?: UploadOptions,
): Promise<Media> => {
  console.log('🎬 Executando CreateMediaCommand:', command);
  
  const { file, ...queryParams } = command;
  const formData = new FormData();
  formData.append('file', file, file.name);

  // Converter camelCase para snake_case para o backend
  const backendParams: any = {};
  if (queryParams.storageProvider) {
    backendParams.storage_provider = queryParams.storageProvider;
  }
  if (queryParams.transcriptionProvider) {
    backendParams.transcription_provider = queryParams.transcriptionProvider;
  }
  if (queryParams.summarizationProvider) {
    backendParams.summarization_provider = queryParams.summarizationProvider;
  }
  if (queryParams.sentimentProvider) {
    backendParams.sentiment_provider = queryParams.sentimentProvider;
  }
  if (queryParams.topicModelingProvider) {
    backendParams.topic_modeling_provider = queryParams.topicModelingProvider;
  }

  const queryString = new URLSearchParams(backendParams).toString();
  const url = queryString ? `/media/?${queryString}` : '/media/';
  
  const response = await api.post<Media>(url, formData, {
    timeout: 300000, // 5 minutos
    onUploadProgress: (event) => {
      if (!event.total) {
        options?.onProgress?.(0, event);
        return;
      }
      const percentCompleted = Math.round((event.loaded * 100) / event.total);
      options?.onProgress?.(percentCompleted, event);
    },
  });
  
  console.log('✅ CreateMediaCommand executado:', response.data);
  return response.data;
};

export const executeReprocessMedia = async (command: ReprocessMediaCommand): Promise<{ message: string }> => {
  console.log('🔄 Executando ReprocessMediaCommand:', command);
  
  const response = await api.post<{ message: string }>(`/media/${command.mediaId}/reprocess`);
  
  console.log('✅ ReprocessMediaCommand executado:', response.data);
  return response.data;
};

// =============================================================================
// AUTH COMMANDS
// =============================================================================

export interface AuthenticateUserCommand {
  email: string;
  password: string;
}

export interface CreateUserCommand {
  email: string;
  password: string;
}

export interface ChangePasswordCommand {
  oldPassword: string;
  newPassword: string;
}

export const executeAuthenticateUser = async (command: AuthenticateUserCommand) => {
  console.log('🔐 Executando AuthenticateUserCommand');

  const response = await authService.login({
    username: command.email,
    password: command.password,
  });

  console.log('✅ AuthenticateUserCommand executado');
  return response;
};

export const executeCreateUser = async (command: CreateUserCommand) => {
  console.log('👤 Executando CreateUserCommand');
  
  const response = await api.post('/auth/register', {
    email: command.email,
    password: command.password,
  });
  
  console.log('✅ CreateUserCommand executado');
  return response.data;
};

export const executeChangePassword = async (command: ChangePasswordCommand) => {
  console.log('🔒 Executando ChangePasswordCommand');
  
  const response = await api.put('/auth/me/password', {
    old_password: command.oldPassword,
    new_password: command.newPassword,
  });
  
  console.log('✅ ChangePasswordCommand executado');
  return response.data;
};

// =============================================================================
// TRANSCRIPTION COMMANDS
// =============================================================================

export interface SetSpeakerAliasesCommand {
  transcriptionId: string;
  aliases: Record<string, string>;
}

export const executeSetSpeakerAliases = async (command: SetSpeakerAliasesCommand) => {
  console.log('🗣️ Executando SetSpeakerAliasesCommand:', command);
  
  const response = await api.put(`/transcriptions/${command.transcriptionId}/speakers`, {
    aliases: command.aliases,
  });
  
  console.log('✅ SetSpeakerAliasesCommand executado');
  return response.data;
};

// =============================================================================
// ADMIN COMMANDS
// =============================================================================

export interface UpdateUserRoleCommand {
  userId: string;
  role: string;
}

export interface DeleteUserCommand {
  userId: string;
}

export interface DeleteMediaCommand {
  mediaId: string;
}

export interface DeleteUserMediaCommand {
  mediaId: string;
}

export const executeUpdateUserRole = async (command: UpdateUserRoleCommand) => {
  console.log('👑 Executando UpdateUserRoleCommand:', command);
  
  const response = await api.put(`/admin/users/${command.userId}`, {
    role: command.role,
  });
  
  console.log('✅ UpdateUserRoleCommand executado');
  return response.data;
};

export const executeDeleteUser = async (command: DeleteUserCommand) => {
  console.log('🗑️ Executando DeleteUserCommand:', command);
  
  await api.delete(`/admin/users/${command.userId}`);
  
  console.log('✅ DeleteUserCommand executado');
};

export const executeDeleteMedia = async (command: DeleteMediaCommand) => {
  console.log('🗑️ Executando DeleteMediaCommand:', command);
  
  await api.delete(`/admin/media/${command.mediaId}`);
  
  console.log('✅ DeleteMediaCommand executado');
};

export const executeDeleteUserMedia = async (command: DeleteUserMediaCommand) => {
  console.log('🗑️ Executando DeleteUserMediaCommand:', command);

  await api.delete(`/media/${command.mediaId}`);

  console.log('✅ DeleteUserMediaCommand executado');
};

export const executeAdminReprocessMedia = async (command: ReprocessMediaCommand) => {
  console.log('🔄 Executando Admin ReprocessMediaCommand:', command);
  
  const response = await api.post(`/admin/media/${command.mediaId}/reprocess`);
  
  console.log('✅ Admin ReprocessMediaCommand executado');
  return response.data;
};
