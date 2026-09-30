import * as React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { ProgressBar } from "@/components/ui/ProgressBar";
import ErrorState from "@/components/ui/ErrorState";
import NumberTicker from "@/components/ui/NumberTicker";
import { MagicSurface } from "@/components/ui/MagicSurface";
import { MediaCard } from "../features/media/components/MediaCard";
import { GenericStatCard } from "@/components/GenericStatCard";
import { useMediaByUserQuery, useMediaStatsQuery } from "@/hooks/useQueries";
import { PaginationState } from "@tanstack/react-table";
import { Input } from "@/components/ui/Input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/Select";
import { useAuth } from "../contexts/AuthContext";
import { UserRole, MediaType, MediaStatus } from "@/types";
import {
  Upload,
  BarChart3,
  FileText,
  Video,
  Music,
  RefreshCw,
  Sparkles,
  Clock3,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

const SelectPageSize = ({
  value,
  onChange,
}: {
  value: number;
  onChange: (n: number) => void;
}) => {
  const options = [12, 24, 48, 96];
  return (
    <Select value={String(value)} onValueChange={(v) => onChange(Number(v))}>
      <SelectTrigger className="w-24">
        <SelectValue placeholder="Itens/pág." />
      </SelectTrigger>
      <SelectContent>
        {options.map((opt) => (
          <SelectItem key={opt} value={String(opt)}>
            {opt} / pág.
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
};

const DashboardPage = () => {
  const [{ pageIndex, pageSize }, setPagination] = React.useState<PaginationState>({
    pageIndex: 0,
    pageSize: 12,
  });
  const [search, setSearch] = React.useState("");
  const [debouncedSearch, setDebouncedSearch] = React.useState("");

  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 400);
    return () => clearTimeout(timer);
  }, [search]);

  const page = pageIndex + 1;

  const { data: mediaPage, isLoading, isError, error, refetch, isFetching } = useMediaByUserQuery(
    page,
    pageSize,
    "desc",
    debouncedSearch
  );
  const { data: statsApi } = useMediaStatsQuery();
  const media = Array.isArray(mediaPage?.items) ? mediaPage.items : [];
  const totalMedia =
    typeof mediaPage?.total === "number"
      ? mediaPage.total
      : Array.isArray(mediaPage?.items)
        ? mediaPage.items.length
        : 0;
  const totalPages = mediaPage?.pages ?? Math.max(1, Math.ceil(totalMedia / pageSize));
  const { user } = useAuth();
  const isAdmin = user?.role === UserRole.ADMIN || user?.role?.toString().toUpperCase().includes("ADMIN");

  // Calcular estatísticas (usa API /media/stats quando disponível; fallback no slice)
  const stats = React.useMemo(() => {
    const fallback = { total: media.length, videos: 0, audios: 0, texts: 0, processing: 0, completed: 0, failed: 0 };
    if (statsApi?.by_status) {
      // A API devolve os estados em minúsculas ("completed"); aceita as duas formas.
      const byStatus = Object.fromEntries(
        Object.entries(statsApi.by_status).map(([k, v]) => [k.toUpperCase(), v]),
      ) as Record<string, number>;
      return {
        total: statsApi.total ?? fallback.total,
        videos: media.filter(m => m.media_type === MediaType.VIDEO).length, // ausência de breakdown por tipo; mantém parcial
        audios: media.filter(m => m.media_type === MediaType.AUDIO).length,
        texts: media.filter(m => m.media_type === MediaType.TEXT).length,
        processing: byStatus.PROCESSING ?? 0,
        completed: byStatus.COMPLETED ?? 0,
        failed: byStatus.FAILED ?? 0,
      };
    }
    return {
      ...fallback,
      videos: media.filter(m => m.media_type === MediaType.VIDEO).length,
      audios: media.filter(m => m.media_type === MediaType.AUDIO).length,
      texts: media.filter(m => m.media_type === MediaType.TEXT).length,
      processing: media.filter(m => m.status === MediaStatus.PROCESSING).length,
      completed: media.filter(m => m.status === MediaStatus.COMPLETED).length,
      failed: media.filter(m => m.status === MediaStatus.FAILED).length,
    };
  }, [media, statsApi]);

  const completionRate = totalMedia ? (stats.completed / totalMedia) * 100 : 0;
  const failureRate = totalMedia ? (stats.failed / totalMedia) * 100 : 0;
  const processingRate = totalMedia ? (stats.processing / totalMedia) * 100 : 0;
  const lastUpload = media?.[0];

  const breakdown = [
    { label: "Vídeo", value: statsApi?.by_type?.VIDEO ?? stats.videos, icon: <Video className="h-4 w-4" />, color: "bg-violet-500" },
    { label: "Áudio", value: statsApi?.by_type?.AUDIO ?? stats.audios, icon: <Music className="h-4 w-4" />, color: "bg-emerald-500" },
    { label: "Texto", value: statsApi?.by_type?.TEXT ?? stats.texts, icon: <FileText className="h-4 w-4" />, color: "bg-sky-500" },
  ];

  const renderStatsCards = () => (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <GenericStatCard
        title="Total monitorado"
        value={totalMedia}
        description={stats.processing ? `${stats.processing} em processamento` : "Nenhum processamento ativo"}
        icon={<FileText className="h-4 w-4" />}
        isLoading={isLoading}
      />
      <GenericStatCard
        title="Taxa de conclusão"
        value={completionRate}
        suffix="%"
        description="Resumo das últimas execuções"
        icon={<CheckCircle2 className="h-4 w-4" />}
        isLoading={isLoading}
      />
      <GenericStatCard
        title="Uploads recentes"
        value={totalMedia}
        description="Total de itens enviados"
        icon={<Upload className="h-4 w-4" />}
        isLoading={isLoading}
      />
      <GenericStatCard
        title="Taxa de falhas"
        value={failureRate}
        suffix="%"
        description={failureRate > 0 ? "Verifique itens com erro" : "Sem falhas no período"}
        icon={<AlertTriangle className="h-4 w-4" />}
        isLoading={isLoading}
      />
    </div>
  );

  const renderContent = () => {
    if (isLoading) {
      return (
        <>
          {/* Stats skeleton */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
          {/* Media grid skeleton */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        </>
      );
    }

    if (isError) {
      return (
        <ErrorState
          title="Erro ao carregar seus arquivos"
          message={error?.message || "Tente novamente em instantes."}
          onRetry={() => refetch()}
        />
      );
    }

    if (!media || media.length === 0) {
      return (
        <div className="text-center py-16">
          <MagicSurface title="Nenhum arquivo encontrado" description="Envie sua primeira mídia para liberar os insights." className="max-w-md mx-auto">
            <Upload className="h-12 w-12 mx-auto text-slate-500 mb-4" />
            <Button asChild className="w-full">
              <Link to="/upload">
                <Upload className="mr-2 h-4 w-4" />
                Fazer Upload
              </Link>
            </Button>
          </MagicSurface>
        </div>
      );
    }

    return (
      <>
        {renderStatsCards()}
        <div className="grid gap-6 lg:grid-cols-3">
          <MagicSurface title="Seus arquivos" description="Consulte e acompanhe o status de cada mídia." className="lg:col-span-2">
            <div className="mb-4 flex gap-2">
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                {isFetching ? "Atualizando..." : "Atualizar"}
              </Button>
              <Input
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPagination((p) => ({ ...p, pageIndex: 0 }));
                }}
                placeholder="Filtrar por nome..."
                className="max-w-xs"
              />
              <Button asChild size="sm">
                <Link to="/upload">
                  <Upload className="mr-2 h-4 w-4" />
                  Novo Upload
                </Link>
              </Button>
            </div>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
              {media.map((item) => (
                <MediaCard key={item.id} media={item} />
              ))}
            </div>
            <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Página {page} de {totalPages} · {totalMedia} itens
              </span>
              <div className="flex gap-2">
                <SelectPageSize value={pageSize} onChange={(n) => setPagination({ pageIndex: 0, pageSize: n })} />
                <Button
                  variant="outline"
                  size="sm"
                  disabled={pageIndex === 0}
                  onClick={() => setPagination((p) => ({ ...p, pageIndex: Math.max(0, p.pageIndex - 1) }))}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() =>
                    setPagination((p) => ({
                      ...p,
                      pageIndex: Math.min(totalPages - 1, p.pageIndex + 1),
                    }))
                  }
                >
                  Próxima
                </Button>
              </div>
            </div>
          </MagicSurface>

          <div className="space-y-4">
            <MagicSurface title="Distribuição por tipo" description="Visão rápida da proporção de mídias enviadas.">
              <div className="space-y-4">
                {breakdown.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-border/70 p-3">
                    <div className="flex items-center justify-between text-sm font-medium">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <span className={`rounded-full p-2 text-slate-900 ${item.color}`}>
                          {item.icon}
                        </span>
                        {item.label}
                      </div>
                      <span>{item.value}</span>
                    </div>
                  </div>
                ))}
              </div>
            </MagicSurface>

            <MagicSurface title="Saúde do pipeline" description="Taxas de processamento em tempo quase real.">
              <div className="space-y-3">
                <ProgressBar label="Concluídos" value={completionRate} color="bg-emerald-500" />
                <ProgressBar label="Processando" value={processingRate} color="bg-sky-500" />
                <ProgressBar label="Falhas" value={failureRate} color="bg-rose-500" />
              </div>
            </MagicSurface>

            <MagicSurface title="Último upload" description="Acompanhe o item mais recente enviado.">
                {lastUpload ? (
                  <div className="space-y-2 text-sm">
                    <p className="font-semibold text-foreground">{lastUpload.filename ?? "Arquivo sem nome"}</p>
                    <p className="text-muted-foreground">
                      Status: <span className="font-medium text-foreground">{lastUpload.status}</span>
                    </p>
                    <p className="text-muted-foreground">
                      Enviado em {new Date(lastUpload.created_at ?? Date.now()).toLocaleString("pt-BR")}
                    </p>
                    <Button asChild variant="secondary" size="sm" className="mt-2 w-full">
                      <Link to={`/media/${lastUpload.id}`}>Abrir detalhes</Link>
                    </Button>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Faça um upload para desbloquear esta visão.</p>
                )}
            </MagicSurface>
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="space-y-6">
      <MagicSurface title="Painel pessoal" description="Centralize uploads, progresso e insights.">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Bem-vindo de volta, {user?.email}</h1>
            <p className="text-sm text-slate-600">Tudo o que você processou e ainda está em fila, reunido neste painel.</p>
          </div>
          <div className="flex flex-col gap-2 text-sm">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-300" />
              <span>{stats.completed} arquivos concluídos</span>
            </div>
            <div className="flex.items-center gap-2">
              <Clock3 className="h-4 w-4 text-sky-300" />
              <span>{stats.processing} em processamento agora</span>
            </div>
            {isAdmin && (
              <Button asChild size="sm" variant="secondary" className="mt-2">
                <Link to="/admin/analytics">
                  <BarChart3 className="mr-2 h-4 w-4" />
                  Visão administrativa
                </Link>
              </Button>
            )}
          </div>
        </div>
      </MagicSurface>
      {renderContent()}
    </div>
  );
};

export default DashboardPage;
