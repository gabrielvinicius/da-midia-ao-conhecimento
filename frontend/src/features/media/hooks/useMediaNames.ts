import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { listMedia } from "../api";

/** Nome do arquivo de cada mídia do usuário (as 100 mais recentes), para as
 *  telas que recebem só o id: revisão, resumos e temas. */
export const useMediaNames = () => {
  const { data } = useQuery({ queryKey: ["media-names"], queryFn: () => listMedia(1, 100), staleTime: 60_000 });
  return useMemo(() => {
    const names = new Map((data?.items ?? []).map((m) => [m.id, m.filename || "Mídia sem nome"]));
    return (id: string | null | undefined) => (id && names.get(id)) || "Mídia";
  }, [data]);
};
