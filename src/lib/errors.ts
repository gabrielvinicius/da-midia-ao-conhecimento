import { isAxiosError } from 'axios';

/**
 * Mensagem para o usuário a partir de um erro da API.
 *
 * O backend responde {"detail": "..."} (erros da aplicação) ou, na validação do
 * FastAPI, {"detail": [{"msg": "..."}]}. Sem nada aproveitável, usa o texto padrão.
 */
export function apiErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: unknown } | undefined;
      if (typeof first?.msg === 'string') return first.msg;
    }
  }
  return fallback;
}

/** Código HTTP da resposta de erro, se houver. */
export function apiErrorStatus(error: unknown): number | undefined {
  return isAxiosError(error) ? error.response?.status : undefined;
}
