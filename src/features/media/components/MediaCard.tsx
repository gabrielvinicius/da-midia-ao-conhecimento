import type { MouseEvent, ReactNode } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Media, MediaStatus, MediaType } from "@/types";
import { FileText, CheckCircle, XCircle, Loader2, Clock, Video, Music, FileImage, MoreVertical, Eye, RotateCcw, Trash2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { useDeleteUserMediaCommand, useReprocessMediaCommand } from "@/hooks/useCommands";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
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

interface MediaCardProps {
  media: Media;
}

// Status configuration for visual feedback
const statusConfig: Record<MediaStatus, { icon: ReactNode; color: string; label: string; bgColor: string }> = {
  [MediaStatus.PENDING]: { 
    icon: <Clock className="h-4 w-4" />, 
    color: "text-yellow-600", 
    label: "Pendente",
    bgColor: "bg-yellow-100 dark:bg-yellow-900/20"
  },
  [MediaStatus.PROCESSING]: { 
    icon: <Loader2 className="h-4 w-4 animate-spin" />, 
    color: "text-blue-600", 
    label: "Processando",
    bgColor: "bg-blue-100 dark:bg-blue-900/20"
  },
  [MediaStatus.COMPLETED]: { 
    icon: <CheckCircle className="h-4 w-4" />, 
    color: "text-green-600", 
    label: "Concluído",
    bgColor: "bg-green-100 dark:bg-green-900/20"
  },
  [MediaStatus.FAILED]: { 
    icon: <XCircle className="h-4 w-4" />, 
    color: "text-red-600", 
    label: "Falhou",
    bgColor: "bg-red-100 dark:bg-red-900/20"
  },
};

// Media type icons
const mediaTypeConfig: Record<MediaType, { icon: ReactNode; label: string; color: string }> = {
  [MediaType.VIDEO]: { icon: <Video className="h-5 w-5" />, label: "Vídeo", color: "text-purple-600" },
  [MediaType.AUDIO]: { icon: <Music className="h-5 w-5" />, label: "Áudio", color: "text-blue-600" },
  [MediaType.TEXT]: { icon: <FileText className="h-5 w-5" />, label: "Texto", color: "text-green-600" },
};

export const MediaCard = ({ media }: MediaCardProps) => {
  const { mutate: reprocess, isPending: isReprocessing } = useReprocessMediaCommand();
  const { mutate: deleteMedia, isPending: isDeleting } = useDeleteUserMediaCommand();
  const { icon: statusIcon, color: statusColor, label: statusLabel, bgColor: statusBgColor } = statusConfig[media.status] || statusConfig[MediaStatus.PENDING];
  const { icon: typeIcon, label: typeLabel, color: typeColor } = mediaTypeConfig[media.media_type] || mediaTypeConfig[MediaType.TEXT];

  const filename = media.filename || media.id;
  const createdAt = new Date(media.created_at);

  const handleReprocess = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    reprocess({ mediaId: media.id });
  };

  return (
    <Card className="group hover:border-primary/50 hover:shadow-md transition-all duration-200 h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className={`${typeColor} flex-shrink-0 translate-y-0.5`}>
              {typeIcon}
            </div>
            <div className="min-w-0 flex-1">
              <CardTitle className="text-base truncate" title={filename}>
                {filename}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                {typeLabel} • {formatDistanceToNow(createdAt, { addSuffix: true, locale: ptBR })}
              </p>
            </div>
          </div>
          <AlertDialog>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                  <span className="sr-only">Abrir menu</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Ações</DropdownMenuLabel>
                <DropdownMenuItem asChild>
                  <Link to={`/media/${media.id}`} className="flex items-center gap-2">
                    <Eye className="h-4 w-4" />
                    Ver detalhes
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-red-600 focus:text-red-600" disabled={isDeleting} asChild>
                  <AlertDialogTrigger asChild>
                    <button className="w-full flex items-center gap-2">
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
                <AlertDialogAction
                  className="bg-red-600 hover:bg-red-700"
                  onClick={() => deleteMedia({ mediaId: media.id })}
                >
                  {isDeleting ? 'Excluindo...' : 'Excluir'}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="flex items-center justify-between mb-4">
          <Badge variant="outline" className={`${statusBgColor} ${statusColor} border-current`}>
            <span className="flex items-center gap-1">
              {statusIcon}
              {statusLabel}
            </span>
          </Badge>
          
          {media.status === MediaStatus.FAILED && (
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={handleReprocess}
              disabled={isReprocessing}
              className="opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
        </div>

        <div className="mt-4 pt-3 border-t">
          <Link to={`/media/${media.id}`} className="block">
            <Button variant="ghost" className="w-full">
              <Eye className="mr-2 h-4 w-4" />
              Ver Detalhes
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
