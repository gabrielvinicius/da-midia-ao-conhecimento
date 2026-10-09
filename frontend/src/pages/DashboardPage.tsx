import * as React from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, BarChart3, CheckCircle2, ChevronLeft, ChevronRight, Files, RefreshCw, Search, Upload, X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/Select";
import { MediaRow } from "@/features/media/components/MediaRow";
import { useMediaByUserQuery, useMediaStatsQuery } from "@/features/media/hooks/useMediaQueries";
import { cn } from "@/lib/utils";
import { isAdminUser, MediaStatus, MediaType } from "@/types";
import { useAuth } from "../contexts/AuthContext";

type StatusFilter = "all" | "active" | "completed" | "failed";

const FILTER_STATUSES: Record<StatusFilter, MediaStatus[]> = {
  all: [],
  active: [MediaStatus.UPLOADED, MediaStatus.PROCESSING, MediaStatus.ANALYZING],
  completed: [MediaStatus.COMPLETED],
  failed: [MediaStatus.FAILED],
};

const FILTER_LABELS: Record<StatusFilter, string> = {
  all: "Todas",
  active: "Em andamento",
  completed: "Concluídas",
  failed: "Com falha",
};

const PAGE_SIZES = [10, 25, 50];

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** Contagens de /media/stats (todas as mídias, sem o filtro da lista). */
const useCounts = () => {
  const { data, isLoading } = useMediaStatsQuery();
  return React.useMemo(() => {
    // A API devolve os estados em minúsculas ("completed"); aceita as duas formas.
    const byStatus = Object.fromEntries(
      Object.entries(data?.by_status ?? {}).map(([k, v]) => [k.toLowerCase(), v]),
    ) as Record<string, number>;
    const of = (statuses: MediaStatus[]) => statuses.reduce((sum, s) => sum + (byStatus[s] ?? 0), 0);
    const byType = data?.by_type ?? {};
    return {
      isLoading,
      known: Boolean(data),
      total: data?.total ?? 0,
      videos: byType[MediaType.VIDEO] ?? 0,
      audios: byType[MediaType.AUDIO] ?? 0,
      texts: byType[MediaType.TEXT] ?? 0,
      byFilter: {
        all: data?.total ?? 0,
        active: of(FILTER_STATUSES.active),
        completed: of(FILTER_STATUSES.completed),
        failed: of(FILTER_STATUSES.failed),
      } as Record<StatusFilter, number>,
    };
  }, [data, isLoading]);
};

type IndicatorProps = {
  label: string;
  value: number;
  detail: string;
  icon: React.ReactNode;
  selected: boolean;
  tone?: "default" | "success" | "danger";
  onClick: () => void;
  isLoading: boolean;
};

/** Indicador que também filtra a lista ao ser tocado. */
const Indicator = ({ label, value, detail, icon, selected, tone = "default", onClick, isLoading }: IndicatorProps) => (
  <button
    type="button"
    onClick={onClick}
    aria-pressed={selected}
    className={cn(
      "rounded-xl border bg-white p-3 text-left transition-colors hover:border-slate-400 sm:p-4",
      selected ? "border-slate-900 ring-1 ring-slate-900" : "border-[#ede4d5]",
    )}
  >
    <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground sm:text-sm">
      <span
        className={cn(
          "hidden sm:inline-flex",
          tone === "success" && "text-emerald-600",
          tone === "danger" && value > 0 && "text-rose-600",
        )}
      >
        {icon}
      </span>
      {label}
    </span>
    {isLoading ? (
      <Skeleton className="mt-2 h-7 w-12" />
    ) : (
      <span className={cn("mt-1 block text-2xl font-semibold sm:text-3xl", tone === "danger" && value > 0 && "text-rose-600")}>
        {value}
      </span>
    )}
    <span className="mt-1 hidden text-xs text-muted-foreground sm:block">{detail}</span>
  </button>
);

const DashboardPage = () => {
  const { user } = useAuth();
  const counts = useCounts();
  const [filter, setFilter] = React.useState<StatusFilter>("all");
  const [search, setSearch] = React.useState("");
  const [debouncedSearch, setDebouncedSearch] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(PAGE_SIZES[0]);

  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 400);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, isLoading, isError, error, refetch, isFetching } = useMediaByUserQuery(
    page,
    pageSize,
    "desc",
    debouncedSearch,
    FILTER_STATUSES[filter],
  );
  const media = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = Math.max(1, data?.pages ?? 1);
  const filtering = filter !== "all" || debouncedSearch !== "";

  const chooseFilter = (next: StatusFilter) => {
    setFilter((current) => (current === next && next !== "all" ? "all" : next));
    setPage(1);
  };
  const clearFilters = () => {
    setFilter("all");
    setSearch("");
    setDebouncedSearch("");
    setPage(1);
  };

  const name = user?.email?.split("@")[0];
  const firstItem = total ? (page - 1) * pageSize + 1 : 0;
  const lastItem = Math.min(total, page * pageSize);
  const completedShare = counts.total ? Math.round((counts.byFilter.completed / counts.total) * 100) : 0;
  const isNewAccount = counts.known && counts.total === 0;

  const renderList = () => {
    if (isLoading) {
      return (
        <div className="space-y-3 py-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      );
    }
    if (isError) {
      return (
        <ErrorState
          title="Não foi possível carregar suas mídias"
          message={error?.message || "Tente novamente em instantes."}
          onRetry={() => refetch()}
        />
      );
    }
    if (media.length === 0) {
      // A busca e os filtros continuam à vista: antes, um nome sem resultado
      // trocava a lista pela tela de "primeira mídia" e escondia o campo.
      return (
        <div className="py-10 text-center">
          <p className="font-medium text-slate-900">Nenhuma mídia encontrada</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {filtering ? "Nada corresponde à busca ou ao filtro escolhido." : "Ainda não há mídias nesta lista."}
          </p>
          {filtering && (
            <Button variant="outline" size="sm" className="mt-4" onClick={clearFilters}>
              Limpar filtros
            </Button>
          )}
        </div>
      );
    }
    return (
      <ul className={cn("divide-y divide-slate-100", isFetching && "opacity-70 transition-opacity")}>
        {media.map((item) => (
          <MediaRow key={item.id} media={item} />
        ))}
      </ul>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-slate-900 [overflow-wrap:anywhere]">Olá{name ? `, ${name}` : ""}</h1>
          <p className="text-sm text-muted-foreground">Suas mídias e o andamento de cada uma.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {isAdminUser(user) && (
            <Button asChild variant="outline">
              <Link to="/admin/analytics">
                <BarChart3 className="mr-2 h-4 w-4" />
                Visão administrativa
              </Link>
            </Button>
          )}
          <Button asChild>
            <Link to="/upload">
              <Upload className="mr-2 h-4 w-4" />
              Enviar mídia
            </Link>
          </Button>
        </div>
      </div>

      {isNewAccount ? (
        <Card className="mx-auto max-w-md border-[#ede4d5] p-8 text-center">
          <Upload className="mx-auto mb-4 h-10 w-10 text-slate-500" />
          <p className="font-semibold text-slate-900">Envie sua primeira mídia</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Aulas, palestras, áudios ou documentos: a plataforma transcreve, resume e organiza o conteúdo.
          </p>
          <Button asChild className="mt-6 w-full">
            <Link to="/upload">Enviar mídia</Link>
          </Button>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 sm:gap-4">
            <Indicator
              label="Mídias"
              value={counts.total}
              detail={`${plural(counts.videos, "vídeo", "vídeos")} · ${plural(counts.audios, "áudio", "áudios")} · ${plural(counts.texts, "texto", "textos")}`}
              icon={<Files className="h-4 w-4" />}
              selected={false}
              onClick={() => chooseFilter("all")}
              isLoading={counts.isLoading}
            />
            <Indicator
              label="Concluídas"
              value={counts.byFilter.completed}
              detail={`${completedShare}% do total`}
              icon={<CheckCircle2 className="h-4 w-4" />}
              tone="success"
              selected={filter === "completed"}
              onClick={() => chooseFilter("completed")}
              isLoading={counts.isLoading}
            />
            <Indicator
              label="Com falha"
              value={counts.byFilter.failed}
              detail={counts.byFilter.failed ? "Toque para ver e tentar de novo" : "Nenhuma falha"}
              icon={<AlertTriangle className="h-4 w-4" />}
              tone="danger"
              selected={filter === "failed"}
              onClick={() => chooseFilter("failed")}
              isLoading={counts.isLoading}
            />
          </div>

          <Card className="border-[#ede4d5] p-4 sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-base font-semibold text-slate-900">Suas mídias</h2>
              <div className="flex gap-2 sm:w-80">
                <div className="relative flex-1">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value);
                      setPage(1);
                    }}
                    placeholder="Buscar pelo nome"
                    aria-label="Buscar pelo nome"
                    className="pl-9 pr-9"
                  />
                  {search && (
                    <button
                      type="button"
                      onClick={() => {
                        setSearch("");
                        setPage(1);
                      }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-slate-900"
                      aria-label="Limpar busca"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                <Button variant="outline" size="icon" onClick={() => refetch()} aria-label="Atualizar lista">
                  <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
                </Button>
              </div>
            </div>

            <div className="-mx-1 mt-4 flex gap-2 overflow-x-auto px-1 pb-1" role="group" aria-label="Filtrar por situação">
              {(Object.keys(FILTER_LABELS) as StatusFilter[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => chooseFilter(key)}
                  aria-pressed={filter === key}
                  className={cn(
                    "whitespace-nowrap rounded-full border px-3 py-1 text-sm transition-colors",
                    filter === key
                      ? "border-slate-900 bg-slate-900 text-white"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-400",
                  )}
                >
                  {FILTER_LABELS[key]}
                  {counts.known && <span className="ml-1.5 opacity-70">{counts.byFilter[key]}</span>}
                </button>
              ))}
            </div>

            <div className="mt-2">{renderList()}</div>

            {total > 0 && (
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4 text-sm text-muted-foreground">
                <span>
                  {firstItem}–{lastItem} de {total}
                </span>
                <div className="flex items-center gap-2">
                  <Select
                    value={String(pageSize)}
                    onValueChange={(v) => {
                      setPageSize(Number(v));
                      setPage(1);
                    }}
                  >
                    <SelectTrigger className="h-8 w-28" aria-label="Itens por página">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PAGE_SIZES.map((n) => (
                        <SelectItem key={n} value={String(n)}>
                          {n} por página
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    aria-label="Página anterior"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    disabled={page >= pages}
                    onClick={() => setPage((p) => Math.min(pages, p + 1))}
                    aria-label="Próxima página"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
};

export default DashboardPage;
