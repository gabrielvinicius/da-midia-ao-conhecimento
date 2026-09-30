import type { QueryClient } from '@tanstack/react-query';

/**
 * Recarrega os dados afetados por um aviso do pipeline.
 *
 * O backend envia todo aviso como `{ kind: "new_notification", payload }`.
 * Quando o aviso se refere a uma mídia (`variables.media_id`), a transcrição,
 * a análise ou o estado dela mudaram: por isso a tela é atualizada sem que o
 * usuário precise recarregar a página.
 */
export const refreshForNotification = (
  queryClient: QueryClient,
  variables: Record<string, unknown> | null | undefined,
): void => {
  const mediaId = variables?.media_id;
  if (typeof mediaId !== 'string' || !mediaId) return;

  queryClient.invalidateQueries({ queryKey: ['media', mediaId] });
  queryClient.invalidateQueries({ queryKey: ['transcription', mediaId] });
  queryClient.invalidateQueries({ queryKey: ['text-analysis', mediaId] });
  queryClient.invalidateQueries({ queryKey: ['media-list'] });
  queryClient.invalidateQueries({ queryKey: ['media-stats'] });
};
