import * as React from "react";
import { ColumnDef, PaginationState } from "@tanstack/react-table";
import { MoreHorizontal, RefreshCw, Recycle, Trash2, CheckCircle, Loader2, ShieldCheck } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

import { Media, MediaStatus } from "@/types";
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

// Define the columns for the media table
export const columns: ColumnDef<Media>[] = [
  {
    accessorKey: "id",
    header: "ID",
  },
  {
    accessorKey: "user_id",
    header: "Usuário",
  },
  {
    accessorKey: "original_file_path",
    header: "Arquivo",
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <MediaStatusBadge status={row.original.status} />,
  },
  {
    accessorKey: "created_at",
    header: "Criada em",
    cell: ({ row }) => format(new Date(row.original.created_at), "PPP p", { locale: ptBR }),
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
        title="Erro ao carregar o inventário de mídias"
        message="Tente novamente em instantes."
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div>
      <div className="flex flex-col gap-4 mb-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Inventário de mídias</h1>
          <p className="text-sm text-muted-foreground">Atue em uploads problemáticos e monitore a operação.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => bulkReprocess()} disabled={isBulkReprocessing}>
            <Recycle className="mr-2 h-4 w-4" />
            {isBulkReprocessing ? 'Iniciando...' : 'Reprocessar falhas'}
          </Button>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 mb-6">
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Mídias listadas</CardTitle>
            <CardDescription>Resultado atual da busca.</CardDescription>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">
            <NumberTicker value={totalItems} />
          </CardContent>
        </Card>
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Em processamento</CardTitle>
            <CardDescription>Itens aguardando workers.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-sky-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-2xl font-semibold">{stats?.processing_media ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Concluídas</CardTitle>
            <CardDescription>Últimos 7 dias.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-emerald-600">
            <CheckCircle className="h-4 w-4" />
            <span className="text-2xl font-semibold">{stats?.completed_media ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Falhas</CardTitle>
            <CardDescription>Prontas para revisão.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-2 text-red-600">
            <ShieldCheck className="h-4 w-4" />
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
            <CardTitle className="text-base font-semibold">Inventário detalhado</CardTitle>
            <CardDescription>Pesquise, filtre e acione ações em lote.</CardDescription>
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
