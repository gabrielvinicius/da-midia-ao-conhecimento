import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { apiErrorMessage } from "@/lib/errors";
import { uploadMedia } from "../api";
import { fileProblem, uploadKind, type UploadKind } from "../uploadFile";

export type UploadStatus = "invalid" | "waiting" | "sending" | "sent" | "failed";

export type UploadItem = {
  id: string;
  file: File;
  kind: UploadKind | null;
  status: UploadStatus;
  progress: number;
  /** Motivo de um arquivo recusado ou de um envio que falhou. */
  message?: string;
  mediaId?: string;
};

export type UploadOptions = { storageProvider: string; transcriptionProvider?: string };

let counter = 0;

/**
 * Fila de envio: vários arquivos de uma vez, enviados um por um (o
 * processamento também é um por vez), com o progresso de cada um. Arquivos
 * recusados ficam na lista com o motivo, sem bloquear os demais.
 */
export const useUploadQueue = () => {
  const queryClient = useQueryClient();
  const [items, setItems] = useState<UploadItem[]>([]);
  const [running, setRunning] = useState(false);
  const itemsRef = useRef<UploadItem[]>([]);

  const update = useCallback((next: (current: UploadItem[]) => UploadItem[]) => {
    setItems((current) => {
      const value = next(current);
      itemsRef.current = value;
      return value;
    });
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
            kind: uploadKind(file),
            status: problem ? "invalid" : "waiting",
            progress: 0,
            message: problem ?? undefined,
          };
        }),
      ]),
    [update],
  );

  const remove = useCallback((id: string) => update((list) => list.filter((i) => i.id !== id)), [update]);

  const clearFinished = useCallback(
    () => update((list) => list.filter((i) => i.status === "waiting" || i.status === "sending")),
    [update],
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
            const media = await uploadMedia(
              {
                file: next.file,
                storageProvider: options.storageProvider,
                // A escolha do transcritor só vale para o que tem fala.
                transcriptionProvider: next.kind === "text" ? undefined : options.transcriptionProvider,
              },
              { onProgress: (percent) => patch(next.id, { progress: percent }) },
            );
            patch(next.id, { status: "sent", progress: 100, mediaId: media.id });
            queryClient.invalidateQueries({ queryKey: ["media"] });
            queryClient.invalidateQueries({ queryKey: ["media-list"] });
          } catch (error) {
            patch(next.id, { status: "failed", message: apiErrorMessage(error, "Não foi possível enviar o arquivo.") });
          }
        }
      } finally {
        setRunning(false);
      }
    },
    [patch, queryClient, running],
  );

  const retry = useCallback((id: string) => patch(id, { status: "waiting", progress: 0, message: undefined }), [patch]);

  return { items, running, add, remove, retry, clearFinished, start };
};
