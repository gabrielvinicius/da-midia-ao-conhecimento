import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Media, MediaStatus, MediaType } from "@/types";
import { FileText, Video, Music, MoreVertical, RotateCcw, Trash2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { useDeleteMediaMutation, useReprocessMediaMutation } from "../hooks/useMediaMutations";
import { useQueryClient } from "@tanstack/react-query";
import { getMedia } from "../api";
import { friendlyError } from "../lib/friendlyError";
import { formatFileSize } from "../uploadFile";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/AlertDialog";

import { MediaStatusBadge } from "@/components/MediaStatusBadge";

const mediaTypeConfig: Record<MediaType, { icon: ReactNode; label: string; color: string }> = {
  [MediaType.VIDEO]: { icon: <Video className="h-4 w-4" />, label: "Vídeo", color: "bg-violet-100 text-violet-700" },
  [MediaType.AUDIO]: { icon: <Music className="h-4 w-4" />, label: "Áudio", color: "bg-emerald-100 text-emerald-700" },
  [MediaType.TEXT]: { icon: <FileText className="h-4 w-4" />, label: "Texto", color: "bg-sky-100 text-sky-700" },
};

/**
 * Uma mídia na lista do painel, numa linha: nome inteiro, tipo, data, tamanho
 * e situação, com as ações à direita. Antes eram cartões altos em três colunas
 * estreitas, que cortavam os nomes ("a-história-não-contad...") e os deixavam
 * iguais entre si.
 */
export const MediaRow = ({ media }: { media: Media }) => {
  const queryClient = useQueryClient();
  const { mutate: reprocess, isPending: isReprocessing } = useReprocessMediaMutation();
  const { mutate: deleteMedia, isPending: isDeleting } = useDeleteMediaMutation();

  const prefetch = () =>
    queryClient.prefetchQuery({ queryKey: ["media", media.id], queryFn: () => getMedia(media.id), staleTime: 30000 });

  const type = mediaTypeConfig[media.media_type] || mediaTypeConfig[MediaType.TEXT];
  const filename = media.filename || media.id;
  const failed = media.status === MediaStatus.FAILED;
  const details = [
    type.label,
    formatDistanceToNow(new Date(media.created_at), { addSuffix: true, locale: ptBR }),
    media.size ? formatFileSize(media.size) : null,
  ].filter(Boolean);

  return (
    <li className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:gap-4" onMouseEnter={prefetch}>
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <span className={`mt-0.5 shrink-0 rounded-full p-2 ${type.color}`} aria-hidden>
          {type.icon}
        </span>
        <div className="min-w-0">
          <Link
            to={`/media/${media.id}`}
            className="font-medium leading-snug text-slate-900 wrap-anywhere hover:underline"
            title={filename}
          >
            {filename}
          </Link>
          <p className="text-xs text-muted-foreground">{details.join(" · ")}</p>
          {failed && media.error_message && (
            // Motivo em linguagem simples; o texto técnico fica na dica e na página da mídia.
            <p className="mt-1 text-xs text-red-700" title={media.error_message}>
              {friendlyError(media.error_message)}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 pl-11 sm:flex-nowrap sm:pl-0">
        <MediaStatusBadge status={media.status} />
        {/* Só mídias que falharam podem ser reprocessadas (regra da API).
            Botão sempre visível e com texto: em telas de toque não há "hover". */}
        {failed && (
          <Button variant="outline" size="sm" onClick={() => reprocess(media.id)} disabled={isReprocessing}>
            <RotateCcw className={`mr-2 h-4 w-4 ${isReprocessing ? "animate-spin" : ""}`} />
            {isReprocessing ? "Enviando..." : "Tentar novamente"}
          </Button>
        )}
        <Button asChild variant="outline" size="sm">
          <Link to={`/media/${media.id}`}>Abrir</Link>
        </Button>
        <AlertDialog>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
                <span className="sr-only">Mais ações para {filename}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem className="text-red-600 focus:text-red-600" disabled={isDeleting} asChild>
                <AlertDialogTrigger asChild>
                  <button className="flex w-full items-center gap-2">
                    <Trash2 className="h-4 w-4" />
                    Excluir mídia
                  </button>
                </AlertDialogTrigger>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Excluir “{filename}”?</AlertDialogTitle>
              <AlertDialogDescription>
                Essa ação remove o arquivo original e todas as transcrições, resumos e análises vinculadas. Não será possível desfazer.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction className="bg-red-600 hover:bg-red-700" onClick={() => deleteMedia(media.id)}>
                {isDeleting ? "Excluindo..." : "Excluir"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </li>
  );
};
