// CQRS Command Hooks - Para operações de escrita
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  executeCreateMedia,
  executeReprocessMedia,
  executeAuthenticateUser,
  executeCreateUser,
  executeChangePassword,
  executeSetSpeakerAliases,
  executeUpdateUserRole,
  executeDeleteUser,
  executeDeleteMedia,
  executeDeleteUserMedia,
  executeAdminReprocessMedia,
  CreateMediaCommand,
  ReprocessMediaCommand,
  AuthenticateUserCommand,
  CreateUserCommand,
  ChangePasswordCommand,
  SetSpeakerAliasesCommand,
  UpdateUserRoleCommand,
  DeleteUserCommand,
  DeleteMediaCommand,
  DeleteUserMediaCommand,
} from '@/api/commands';
import {
  getCurrentUser,
  getProviders,
  ProvidersResponse,
} from '@/api/queries';
import { useAuth } from '@/contexts/AuthContext';
import { apiErrorMessage } from '@/lib/errors';
import { removeFromCachedPages, restoreCachedPages } from '@/lib/optimistic';

// =============================================================================
// MEDIA COMMANDS
// =============================================================================

export const useCreateMediaCommand = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: (command: CreateMediaCommand) =>
      executeCreateMedia(command, {
        onProgress: (percent) => setProgress(percent),
      }),
    onMutate: () => {
      setProgress(0);
    },
    onSuccess: (data) => {
      toast.success(`Arquivo "${data.filename || 'arquivo'}" enviado. Você será avisado quando o processamento terminar.`);
      setProgress(100);
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['media'] });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      
      navigate('/dashboard');
    },
    onError: (error) => {
      console.error('❌ CreateMediaCommand falhou:', error);
      setProgress(0);
      toast.error(apiErrorMessage(error, 'Erro ao fazer upload do arquivo'));
    },
  });

  return { ...mutation, progress };
};

export const useReprocessMediaCommand = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (command: ReprocessMediaCommand) => executeReprocessMedia(command),
    onSuccess: (_data, variables) => {
      toast.info('Processamento reiniciado. Você será avisado quando terminar.');

      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['media', variables.mediaId] });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      queryClient.invalidateQueries({ queryKey: ['transcription', variables.mediaId] });
      queryClient.invalidateQueries({ queryKey: ['text-analysis', variables.mediaId] });
      queryClient.invalidateQueries({ queryKey: ['media-stats'] });
    },
    onError: (error) => {
      // 409: a mídia não falhou (já foi reenviada ou está em processamento).
      toast.error(apiErrorMessage(error, 'Não foi possível reprocessar a mídia'));
    },
  });
};

export const useDeleteUserMediaCommand = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (command: DeleteUserMediaCommand) => executeDeleteUserMedia(command),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: ['media-list'] });
      return { previous: removeFromCachedPages(queryClient, ['media-list'], variables.mediaId) };
    },
    onSuccess: (_, variables) => {
      toast.success('Mídia excluída com sucesso.');
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      queryClient.invalidateQueries({ queryKey: ['media-stats'] });
      if (variables.mediaId) {
        queryClient.invalidateQueries({ queryKey: ['media', variables.mediaId] });
        queryClient.removeQueries({ queryKey: ['media', variables.mediaId] });
      }
    },
    onError: (error, _vars, context) => {
      console.error('❌ DeleteMediaCommand falhou:', error);
      const message = apiErrorMessage(error, 'Erro ao excluir a mídia');
      toast.error(message);
      restoreCachedPages(queryClient, context?.previous);
    },
  });
};

// =============================================================================
// AUTH COMMANDS
// =============================================================================

// =============================================================================
// TRANSCRIPTION COMMANDS
// =============================================================================

// =============================================================================
// ADMIN COMMANDS
// =============================================================================
