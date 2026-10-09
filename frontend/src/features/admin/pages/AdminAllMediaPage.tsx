import * as React from "react";
import { ColumnDef, PaginationState } from "@tanstack/react-table";
import { MoreHorizontal, RefreshCw, Recycle, Trash2, CheckCircle, Loader2, XCircle } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

import { Link } from "react-router-dom";
import { Media, MediaStatus } from "@/types";
import type { AdminMedia } from "../api";
import { formatFileSize } from "@/features/media/uploadFile";
import { useAllMedia, useSystemStats } from "../hooks/useAdminQueries";
import { useDeleteMedia, useReprocessMedia, useBulkReprocessMedia } from "../hooks/useAdminMutations";
import { DataTable } from "@/components/ui/DataTable";
import { MediaStatusBadge } from "@/components/MediaStatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import NumberTicker from "@/components/ui/NumberTicker";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
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

// Action Cell Component for Media
const MediaActionsCell = ({ media }: { media: Media }) => {
  const { mutate: deleteMedia, isPending: isDeleting } = useDeleteMedia();
  const { mutate: reprocessMedia, isPending: isReprocessing } = useReprocessMedia();

  const canReprocess = media.status === MediaStatus.FAILED;

  return (
    <AlertDialog>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-8 w-8 p-0">
            <span className="sr-only">Abrir ações</span>
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Ações</DropdownMenuLabel>
          <DropdownMenuItem
            onClick={() => reprocessMedia(media.id)}
            disabled={!canReprocess || isReprocessing}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {isReprocessing ? "Iniciando..." : "Reprocessar"}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="text-red-600" disabled={isDeleting} asChild>
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
          <AlertDialogTitle>Excluir “{media.filename || 'arquivo'}”?</AlertDialogTitle>
          <AlertDialogDescription>
            Essa ação remove o arquivo, transcrições e análises relacionadas. Não será possível desfazer.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={() => deleteMedia(media.id)} className="bg-red-600 hover:bg-red-700">
            {isDeleting ? "Excluindo..." : "Excluir"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};

const TYPE_LABELS: Record<string, string> = { video: "Vídeo", audio: "Áudio", text: "Texto" };

// Antes, a tabela mostrava o id da mídia e o id do dono, e a coluna "Arquivo"
// lia um campo que a API não devolve (ficava vazia).
export const columns: ColumnDef<AdminMedia>[] = [
  {
    accessorKey: "filename",
    header: "Arquivo",
    cell: ({ row }) => (
      <div className="min-w-0 max-w-xs">
        <Link to={`/media/${row.original.id}`} className="font-medium text-slate-900 [overflow-wrap:anywhere] hover:underline">
          {row.original.filename || row.original.id}
        </Link>
        <p className="text-xs text-muted-foreground">
          {[TYPE_LABELS[row.original.media_type] ?? row.original.media_type, row.original.size ? formatFileSize(row.original.size) : null]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
    ),
  },
  {
    accessorKey: "owner_email",
    header: "Dono",
    cell: ({ row }) => <span className="[overflow-wrap:anywhere]">{row.original.owner_email ?? "—"}</span>,
  },
  {
    accessorKey: "status",
    header: "Situação",
    cell: ({ row }) => <MediaStatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "created_at",
    header: "Enviada em",
    cell: ({ row }) => format(new Date(row.original.created_at), "dd/MM/yyyy HH:mm", { locale: ptBR }),
  },
  {
    id: "actions",
    cell: ({ row }) => <MediaActionsCell media={row.original} />,
  },
];

export const AdminAllMediaPage = () => {
  const [{ pageIndex, pageSize }, setPagination] = React.useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });
  const [search, setSearch] = React.useState('');

  const { mutate: bulkReprocess, isPending: isBulkReprocessing } = useBulkReprocessMedia();

  const { data, isLoading, isError, refetch } = useAllMedia({
    page: pageIndex + 1, // API is 1-indexed
    limit: pageSize,
    search,
  });

  const defaultData = React.useMemo(() => [], []);
  const items = data?.items ?? defaultData;
  const totalItems = data?.total ?? 0;
  const totalPages = data?.pages ?? Math.max(1, Math.ceil(totalItems / pageSize));
  // Contagens de todo o sistema (a listagem traz só a página atual).
  const { data: stats } = useSystemStats();

  const pagination = React.useMemo(
    () => ({ pageIndex, pageSize }),
    [pageIndex, pageSize]
  );

  if (isError) {
    return (
      <ErrorState
        title="Não foi possível carregar as mídias"
        message="Tente novamente em instantes."
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div>
      <div className="flex flex-col gap-4 mb-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Mídias</h1>
          <p className="text-sm text-muted-foreground">Atue nos envios com problema e acompanhe a operação.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {/* Confirmação: o lote ocupa a GPU por um bom tempo (até 50 mídias). */}
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" disabled={isBulkReprocessing || !stats?.failed_media}>
                <Recycle className="mr-2 h-4 w-4" />
                {isBulkReprocessing ? 'Iniciando...' : 'Reprocessar falhas'}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Reprocessar as mídias com falha?</AlertDialogTitle>
                <AlertDialogDescription>
                  Até 50 mídias voltam para a fila, uma de cada vez na GPU; enquanto isso, os novos envios esperam mais.
                  Os resultados anteriores delas são apagados.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancelar</AlertDialogCancel>
                <AlertDialogAction onClick={() => bulkReprocess()}>Reprocessar</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 mb-6">
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Mídias listadas</CardTitle>
            <CardDescription>Resultado da busca atual.</CardDescription>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">
            <NumberTicker value={totalItems} />
          </CardContent>
        </Card>
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Em processamento</CardTitle>
            <CardDescription>
              Transcrição ou análise em andamento.{" "}
              <Link to="/admin/queue" className="underline">Ver fila</Link>
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-sky-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-2xl font-semibold">{stats?.processing_media ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Concluídas</CardTitle>
            <CardDescription>Desde o início.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-emerald-600">
            <CheckCircle className="h-4 w-4" />
            <span className="text-2xl font-semibold">{stats?.completed_media ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Falhas</CardTitle>
            <CardDescription>Podem ser reprocessadas.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-red-600">
            <XCircle className="h-4 w-4" />
            <span className="text-2xl font-semibold">{stats?.failed_media ?? 0}</span>
          </CardContent>
        </Card>
      </div>
      {isLoading && !data ? (
        <div className="space-y-4">
          <Skeleton className="h-12 w-1/3" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : (
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Todas as mídias</CardTitle>
            <CardDescription>De todos os usuários, das mais novas para as mais antigas.</CardDescription>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={columns}
              data={items}
              pageCount={Math.max(1, totalPages)}
              pagination={pagination}
              onPaginationChange={setPagination}
              onSearchChange={setSearch}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
};
