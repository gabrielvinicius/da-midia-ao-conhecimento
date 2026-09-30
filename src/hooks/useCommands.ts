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
      const filename = data.filename || 'arquivo';
      const pipeline = data.processing_pipeline?.join(' → ');
      const correlationId = (data as any)?.correlation_id;

      const successMsg = pipeline
        ? `Arquivo "${filename}" enviado. Pipeline: ${pipeline}`
        : `Arquivo "${filename}" enviado.`;

      toast.success(successMsg + (correlationId ? ` (correlation_id: ${correlationId})` : ''));
      setProgress(100);
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['media'] });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      
      navigate('/dashboard');
    },
    onError: (error: any) => {
      console.error('❌ CreateMediaCommand falhou:', error);
      setProgress(0);
      
      const payload = error?.response?.data;
      const errorMessage =
        payload?.message ||
        payload?.error ||
        payload?.detail ||
        error?.message ||
        'Erro ao fazer upload do arquivo';

      if (error?.response?.headers?.['x-correlation-id']) {
        console.warn('correlation_id:', error.response.headers['x-correlation-id']);
      }
      
      toast.error(errorMessage);
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
    onError: (error: any) => {
      // 409: a mídia não falhou (já foi reenviada ou está em processamento).
      const detail = error?.response?.data?.detail;
      toast.error(typeof detail === 'string' && detail ? detail : 'Não foi possível reprocessar a mídia');
    },
  });
};

export const useDeleteUserMediaCommand = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (command: DeleteUserMediaCommand) => executeDeleteUserMedia(command),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: ['media-list'] });
      const previous = queryClient.getQueryData<any>(['media-list']);

      // Otimista: remove item da primeira página em cache se existir
      if (previous && Array.isArray(previous.items)) {
        const items = previous.items.filter((m: any) => m.id !== variables.mediaId);
        const total = typeof previous.total === 'number' ? Math.max(0, previous.total - 1) : items.length;
        queryClient.setQueryData(['media-list'], { ...previous, items, total });
      }

      return { previous };
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
    onError: (error: any, _vars, context) => {
      console.error('❌ DeleteMediaCommand falhou:', error);
      const message = error?.response?.data?.detail || 'Erro ao excluir a mídia';
      toast.error(message);
      if (context?.previous) {
        queryClient.setQueryData(['media-list'], context.previous);
      }
    },
  });
};

// =============================================================================
// AUTH COMMANDS
// =============================================================================

export const useAuthenticateUserCommand = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setUser } = useAuth();

  return useMutation({
    mutationFn: (command: AuthenticateUserCommand) => executeAuthenticateUser(command),
    onSuccess: async (data) => {
      try {
        // Buscar dados do usuário após login
      const user = await getCurrentUser();
        
        setUser(user);
        queryClient.setQueryData(['current-user'], user);
        
        toast.success('Login realizado com sucesso!');
        navigate('/dashboard');
      } catch (userError) {
        console.error('Erro ao buscar dados do usuário:', userError);
        toast.error('Erro ao carregar dados do usuário');
      }
    },
    onError: (error: any) => {
      console.error('❌ AuthenticateUserCommand falhou:', error);
      const message = error?.response?.data?.detail || 'Credenciais inválidas';
      toast.error(message);
    },
  });
};

export const useCreateUserCommand = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (command: CreateUserCommand) => executeCreateUser(command),
    onSuccess: () => {
      toast.success('Usuário criado com sucesso! Faça login para continuar.');
      navigate('/login');
    },
    onError: (error: any) => {
      console.error('❌ CreateUserCommand falhou:', error);
      const message = error?.response?.data?.detail || 'Erro ao criar usuário';
      toast.error(message);
    },
  });
};

export const useChangePasswordCommand = () => {
  return useMutation({
    mutationFn: (command: ChangePasswordCommand) => executeChangePassword(command),
    onSuccess: () => {
      toast.success('Senha alterada com sucesso!');
    },
    onError: (error: any) => {
      console.error('❌ ChangePasswordCommand falhou:', error);
      const message = error?.response?.data?.detail || 'Erro ao alterar senha';
      toast.error(message);
    },
  });
};

// =============================================================================
// TRANSCRIPTION COMMANDS
// =============================================================================

export const useSetSpeakerAliasesCommand = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (command: SetSpeakerAliasesCommand) => executeSetSpeakerAliases(command),
    onSuccess: (data, variables) => {
      toast.success('Nomes dos falantes atualizados!');
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['transcription', variables.transcriptionId] });
      queryClient.setQueryData(['transcription', variables.transcriptionId], data);
    },
    onError: (error: any) => {
      console.error('❌ SetSpeakerAliasesCommand falhou:', error);
      toast.error('Erro ao atualizar nomes dos falantes');
    },
  });
};

// =============================================================================
// ADMIN COMMANDS
// =============================================================================

export const useUpdateUserRoleCommand = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (command: UpdateUserRoleCommand) => executeUpdateUserRole(command),
    onSuccess: (data) => {
      toast.success(`Role do usuário atualizada para ${data.role}`);
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
    },
    onError: (error: any) => {
      console.error('❌ UpdateUserRoleCommand falhou:', error);
      toast.error('Erro ao atualizar role do usuário');
    },
  });
};

export const useDeleteUserCommand = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (command: DeleteUserCommand) => executeDeleteUser(command),
    onSuccess: () => {
      toast.success('Usuário removido com sucesso');
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
    },
    onError: (error: any) => {
      console.error('❌ DeleteUserCommand falhou:', error);
      toast.error('Erro ao remover usuário');
    },
  });
};

export const useDeleteMediaCommand = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (command: DeleteMediaCommand) => executeDeleteMedia(command),
    onSuccess: () => {
      toast.success('Mídia removida com sucesso');
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['admin', 'media'] });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
    },
    onError: (error: any) => {
      console.error('❌ DeleteMediaCommand falhou:', error);
      toast.error('Erro ao remover mídia');
    },
  });
};

export const useAdminReprocessMediaCommand = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (command: ReprocessMediaCommand) => executeAdminReprocessMedia(command),
    onSuccess: (data, variables) => {
      toast.info(data.message);
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['admin', 'media'] });
      queryClient.invalidateQueries({ queryKey: ['media', variables.mediaId] });
    },
    onError: (error: any) => {
      console.error('❌ Admin ReprocessMediaCommand falhou:', error);
      toast.error('Erro ao reprocessar mídia (admin)');
    },
  });
};
