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
  // Painel do administrador: a lista de todas as mídias e as contagens.
  queryClient.invalidateQueries({ queryKey: ['admin-all-media'] });
  queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
};

/**
 * Agrupa os avisos que chegam logo depois de a conexão abrir.
 *
 * Ao reconectar, o servidor reenvia de uma vez os avisos pendentes (até 50);
 * um toast para cada um cobria a tela. Durante `windowMs` após `open()`, os
 * avisos são contados e viram um só toast; depois, cada aviso tem o seu.
 */
export const createNoticeBatcher = (
  show: (message: string) => void,
  windowMs = 1500,
) => {
  let buffered: string[] = [];
  let timer: ReturnType<typeof setTimeout> | null = null;

  const flush = () => {
    timer = null;
    if (buffered.length === 1) show(buffered[0]);
    else if (buffered.length > 1) show(`Você tem ${buffered.length} avisos novos.`);
    buffered = [];
  };

  const cancel = () => {
    if (timer) clearTimeout(timer);
    timer = null;
    buffered = [];
  };

  return {
    open() {
      cancel();
      timer = setTimeout(flush, windowMs);
    },
    push(message: string) {
      if (timer) buffered.push(message);
      else show(message);
    },
    cancel,
  };
};
