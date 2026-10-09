import * as React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PlayCircle, Search } from "lucide-react";

import { Card } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { useMediaNames } from "@/features/media/hooks/useMediaNames";
import { getTopicsOverview, type TopicGroup } from "@/features/summarization/api";
import { normalizeText } from "@/lib/text";
import { formatClock } from "@/lib/time";
import { cn } from "@/lib/utils";

type Filter = "shared" | "all";

const TopicCard = ({ group, nameOf }: { group: TopicGroup; nameOf: (id: string | null) => string }) => (
  <li className="rounded-xl border border-[#ede4d5] bg-white p-4">
    <div className="flex items-start justify-between gap-3">
      <h2 className="font-semibold text-slate-900">{group.title}</h2>
      {group.media_count > 1 && (
        <span className="flex-shrink-0 whitespace-nowrap rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-800">
          em {group.media_count} mídias
        </span>
      )}
    </div>
    <ul className="mt-3 space-y-3">
      {group.occurrences.map((o) => (
        <li key={`${o.analysis_id}-${o.title}`} className="border-l-2 border-slate-200 pl-3 text-sm">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <Link to={o.media_id ? `/media/${o.media_id}` : "#"} className="font-medium text-slate-900 [overflow-wrap:anywhere] hover:underline">
              {nameOf(o.media_id)}
            </Link>
            {o.media_id && o.start != null && (
              <Link
                to={`/media/${o.media_id}?t=${Math.floor(o.start)}`}
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-slate-900"
              >
                <PlayCircle className="h-3.5 w-3.5" />
                {formatClock(o.start)}
              </Link>
            )}
          </div>
          {o.snippet && <p className="mt-1 line-clamp-2 text-muted-foreground">“{o.snippet}”</p>}
          {o.keywords.length > 0 && <p className="mt-1 text-xs text-muted-foreground">{o.keywords.join(" · ")}</p>}
        </li>
      ))}
    </ul>
  </li>
);

/**
 * Temas de todas as mídias, juntos pelo título: mostra como o conteúdo das
 * aulas se conecta e leva a cada trecho onde o tema aparece.
 */
const TopicsPage = () => {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["topics-overview"], queryFn: getTopicsOverview });
  const nameOf = useMediaNames();
  const [search, setSearch] = React.useState("");
  const all = React.useMemo(() => data ?? [], [data]);
  const sharedCount = all.filter((g) => g.media_count > 1).length;
  const [filter, setFilter] = React.useState<Filter>("all");

  const groups = React.useMemo(() => {
    const term = normalizeText(search.trim());
    return all.filter(
      (g) =>
        (filter === "all" || g.media_count > 1) &&
        (!term || normalizeText(`${g.title} ${g.occurrences.flatMap((o) => o.keywords).join(" ")}`).includes(term)),
    );
  }, [all, filter, search]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Temas</h1>
        <p className="text-sm text-muted-foreground">
          Os assuntos de todas as suas mídias. Os que aparecem em mais de uma vêm primeiro: é ali que as aulas se conectam.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative w-full sm:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar tema ou palavra-chave" aria-label="Buscar tema" className="pl-9" />
        </div>
        <div className="flex gap-2" role="group" aria-label="Quais temas">
          {(
            [
              ["all", `Todos (${all.length})`],
              ["shared", `Em mais de uma mídia (${sharedCount})`],
            ] as [Filter, string][]
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
              className={cn(
                "whitespace-nowrap rounded-full border px-3 py-1 text-sm",
                filter === value ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 text-slate-700 hover:border-slate-400",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-3 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState title="Não foi possível carregar os temas" message="Tente novamente em instantes." onRetry={() => refetch()} />
      ) : all.length === 0 ? (
        <Card className="border-[#ede4d5] p-8 text-center">
          <p className="font-medium text-slate-900">Nenhum tema ainda</p>
          <p className="mt-1 text-sm text-muted-foreground">Os temas aparecem quando a análise das suas mídias termina.</p>
        </Card>
      ) : groups.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Nenhum tema encontrado.</p>
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {groups.map((group) => (
            <TopicCard key={group.title} group={group} nameOf={nameOf} />
          ))}
        </ul>
      )}
    </div>
  );
};

export default TopicsPage;
