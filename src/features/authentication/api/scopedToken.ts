import api from "@/lib/api";

/**
 * Token de finalidade restrita, para onde o navegador não manda cabeçalho:
 * a URL do <video> (por mídia, válido por horas) e a abertura do WebSocket
 * de avisos (válido por minutos). O token de acesso não vai mais na URL.
 */
export type ScopedPurpose = "media_stream" | "notifications";

export const requestScopedToken = async (purpose: ScopedPurpose, resource?: string): Promise<string> => {
  const response = await api.post<{ token: string; expires_in: number }>("/auth/scoped-token", {
    purpose,
    resource,
  });
  return response.data.token;
};
