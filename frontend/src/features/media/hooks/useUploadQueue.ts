import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { apiErrorMessage } from "@/lib/errors";
import type { Media } from "@/types";
import { importMediaFromUrl, uploadMedia } from "../api";
import { fileProblem, uploadKind, type UploadKind } from "../uploadFile";

export type UploadStatus = "invalid" | "waiting" | "sending" | "sent" | "failed";

export type UploadItem = {
  id: string;
  /** Arquivo do computador, ou ``url`` de um vídeo do YouTube. */
  file?: File;
  url?: string;
  /** Nome mostrado: o do arquivo, o link e, depois da importação, o título do vídeo. */
  name: string;
  kind: UploadKind | null;
  status: UploadStatus;
  progress: number;
  /** Motivo de um arquivo recusado ou de um envio que falhou. */
  message?: string;
  mediaId?: string;
};

export type UploadOptions = { storageProvider: string; transcriptionProvider?: string };

let counter = 0;

const YOUTUBE_LINK = /^https?:\/\/(www\.|m\.|music\.)?(youtube\.com|youtu\.be)\//i;

export const isYoutubeLink = (url: string) => YOUTUBE_LINK.test(url.trim());

/** Mensagem de erro de um link, ou null se ele pode ser importado (o servidor confere o resto). */
export const linkProblem = (url: string): string | null =>
  /^https?:\/\/[^\s/]+\.[^\s]+$/i.test(url.trim()) ? null : "Cole um link completo, começando com http:// ou https://.";

/**
 * Fila de envio: vários arquivos (e links do YouTube) de uma vez, enviados um
 * por um (o processamento também é um por vez), com o progresso de cada um.
 * Itens recusados ficam na lista com o motivo, sem bloquear os demais.
 */
export const useUploadQueue = () => {
  const queryClient = useQueryClient();
  const [items, setItems] = useState<UploadItem[]>([]);
  const [running, setRunning] = useState(false);
  const itemsRef = useRef<UploadItem[]>([]);

  // A ref é a fonte da lista: o laço de envio a lê logo depois de cada
  // mudança. Antes, ela era gravada dentro da função passada ao setItems, que
  // o React 19 pode rodar só na renderização seguinte; o laço achava o mesmo
  // item ainda "waiting" e o enviava de novo, sem parar.
  const update = useCallback((next: (current: UploadItem[]) => UploadItem[]) => {
    const value = next(itemsRef.current);
    itemsRef.current = value;
    setItems(value);
  }, []);

  const patch = useCallback(
    (id: string, change: Partial<UploadItem>) => update((list) => list.map((i) => (i.id === id ? { ...i, ...change } : i))),
    [update],
  );

  const add = useCallback(
    (files: FileList | File[]) =>
      update((list) => [
        ...list,
        ...Array.from(files).map((file): UploadItem => {
          const problem = fileProblem(file);
          return {
            id: `up-${++counter}`,
            file,
            name: file.name,
            kind: uploadKind(file),
            status: problem ? "invalid" : "waiting",
            progress: 0,
            message: problem ?? undefined,
          };
        }),
      ]),
    [update],
  );

  const addLink = useCallback(
    (url: string) =>
      update((list) => [
        ...list,
        {
          id: `up-${++counter}`,
          url: url.trim(),
          name: url.trim(),
          // Pelo final do endereço (".../aula.mp3"); sem extensão, o tipo só se sabe depois.
          kind: isYoutubeLink(url) ? "video" : uploadKind({ name: url.trim().split(/[?#]/)[0] }),
          status: "waiting",
          progress: 0,
        },
      ]),
    [update],
  );

  const remove = useCallback((id: string) => update((list) => list.filter((i) => i.id !== id)), [update]);

  const clearFinished = useCallback(
    () => update((list) => list.filter((i) => i.status === "waiting" || i.status === "sending")),
    [update],
  );

  const send = useCallback(
    (item: UploadItem, options: UploadOptions): Promise<Media> =>
      item.url
        ? importMediaFromUrl(item.url, options.storageProvider, options.transcriptionProvider)
        : uploadMedia(
            {
              file: item.file!,
              storageProvider: options.storageProvider,
              // A escolha do transcritor só vale para o que tem fala.
              transcriptionProvider: item.kind === "text" ? undefined : options.transcriptionProvider,
            },
            { onProgress: (percent) => patch(item.id, { progress: percent }) },
          ),
    [patch],
  );

  const start = useCallback(
    async (options: UploadOptions) => {
      if (running) return;
      setRunning(true);
      try {
        for (;;) {
          const next = itemsRef.current.find((i) => i.status === "waiting");
          if (!next) break;
          patch(next.id, { status: "sending", progress: 0, message: undefined });
          try {
            const media = await send(next, options);
            patch(next.id, {
              status: "sent",
              progress: 100,
              mediaId: media.id,
              name: next.url ? media.filename || next.name : next.name,
              kind: next.url ? (media.media_type as UploadKind) ?? next.kind : next.kind,
            });
            queryClient.invalidateQueries({ queryKey: ["media"] });
            queryClient.invalidateQueries({ queryKey: ["media-list"] });
          } catch (error) {
            patch(next.id, { status: "failed", message: apiErrorMessage(error, "Não foi possível enviar.") });
          }
        }
      } finally {
        setRunning(false);
      }
    },
    [patch, queryClient, running, send],
  );

  const retry = useCallback((id: string) => patch(id, { status: "waiting", progress: 0, message: undefined }), [patch]);

  return { items, running, add, addLink, remove, retry, clearFinished, start };
};
