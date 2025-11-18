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
} from '@/api/commands';
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
      const filename = data.original_file_path?.split('/').pop() || 'arquivo';
      toast.success(`Arquivo "${filename}" enviado com sucesso! Pipeline: ${data.processing_pipeline?.join(' → ')}`);
      setProgress(100);
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['media'] });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      
      navigate('/dashboard');
    },
    onError: (error: any) => {
      console.error('❌ CreateMediaCommand falhou:', error);
      setProgress(0);
      
      let errorMessage = 'Erro ao fazer upload do arquivo';
      if (error?.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error?.message) {
        errorMessage = error.message;
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
    onSuccess: (data, variables) => {
      toast.info(data.message);
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['media', variables.mediaId] });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      queryClient.invalidateQueries({ queryKey: ['transcription', variables.mediaId] });
      queryClient.invalidateQueries({ queryKey: ['summary', variables.mediaId] });
      queryClient.invalidateQueries({ queryKey: ['sentiment-analysis', variables.mediaId] });
      queryClient.invalidateQueries({ queryKey: ['topic-modeling', variables.mediaId] });
    },
    onError: (error: any) => {
      console.error('❌ ReprocessMediaCommand falhou:', error);
      toast.error('Erro ao reprocessar arquivo');
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
        const { getCurrentUser } = await import('@/api/queries');
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
