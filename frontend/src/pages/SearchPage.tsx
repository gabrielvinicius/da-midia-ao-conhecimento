import { FormEvent, useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Clock, FileText, History, Loader2, Music, PlayCircle, Search, SearchX, Video, X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { getMedia } from "@/features/media/api";
import { semanticSearch, type SemanticSearchResult } from "@/features/summarization/api";
import { formatClock } from "@/lib/time";
import { cn } from "@/lib/utils";
import { MediaType, type Media } from "@/types";

const MIN_QUERY_LENGTH = 3;
const RESULT_LIMIT = 20;
const RECENT_KEY = "busca-recentes";

export const formatTimestamp = (seconds?: number | null): string | null =>
  seconds == null || Number.isNaN(seconds) ? null : formatClock(seconds);

const EXAMPLES = ["Quem escreveu o manifesto ágil?", "o que é programação estruturada", "decisões tomadas na reunião"];

const MATCH: Record<string, { label: string; className: string }> = {
  strong: { label: "Trata disso", className: "bg-emerald-50 text-emerald-800" },
  related: { label: "Relacionado", className: "bg-sky-50 text-sky-800" },
  weak: { label: "Pode ter relação", className: "bg-slate-100 text-slate-600" },
  unrecognized: { label: "Pouca relação", className: "bg-amber-50 text-amber-800" },
};

const TYPE_ICON: Record<string, ReactNode> = {
  [MediaType.VIDEO]: <Video className="h-4 w-4" />,
  [MediaType.AUDIO]: <Music className="h-4 w-4" />,
};

// Buscas recentes ficam só neste navegador (comodidade); qualquer falha é ignorada.
const readRecent = (): string[] => {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]").slice(0, 6);
  } catch {
    return [];
  }
};
const saveRecent = (list: string[]) => {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, 6)));
  } catch {
    /* sem armazenamento: só não lembra */
  }
};

const normalize = (text: string) => text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Destaca as palavras da pergunta que aparecem no trecho (a busca é por significado; isto só ajuda a ler). */
const highlight = (text: string, query: string): ReactNode[] => {
  const words = new Set(normalize(query).split(/[^\p{L}\p{N}]+/u).filter((w) => w.length >= 4));
  if (!words.size) return [text];
  return text.split(/([\p{L}\p{N}]+)/u).map((part, i) =>
    words.has(normalize(part)) ? <mark key={i} className="rounded bg-amber-100 px-0.5 text-inherit">{part}</mark> : part,
  );
};

type Group = { mediaId: string; title?: string | null; results: SemanticSearchResult[] };

/** Resultados agrupados por mídia, na ordem do melhor trecho de cada uma. */
const groupByMedia = (results: SemanticSearchResult[]): Group[] => {
  const groups = new Map<string, Group>();
  for (const result of results) {
    const group = groups.get(result.media_id) ?? { mediaId: result.media_id, title: result.title, results: [] };
    group.results.push(result);
    groups.set(result.media_id, group);
  }
  return [...groups.values()];
};

/**
 * Busca por significado em todo o acervo do usuário. Os resultados vêm
 * agrupados por mídia, com o título do conteúdo, o momento de cada trecho e
 * quanto ele trata da pergunta; um clique abre a mídia naquele momento.
 */
const SearchPage = () => {
  const [params, setParams] = useSearchParams();
  const query = (params.get("q") ?? "").trim();
  const [input, setInput] = useState(query);
  const [recent, setRecent] = useState<string[]>(readRecent);

  // O campo acompanha a busca do endereço quando ela muda (voltar, links).
  const [shownQuery, setShownQuery] = useState(query);
  if (query !== shownQuery) {
    setShownQuery(query);
    setInput(query);
  }

  const { data, isFetching, isError } = useQuery({
    queryKey: ["semantic-search", query],
    queryFn: () => semanticSearch(query, RESULT_LIMIT),
    enabled: query.length >= MIN_QUERY_LENGTH,
    staleTime: 60_000,
  });
  const groups = useMemo(() => groupByMedia(data ?? []), [data]);
  // Nome e tipo de cada mídia encontrada (o mesmo cache da página da mídia).
  const medias = useQueries({
    queries: groups.map((g) => ({ queryKey: ["media", g.mediaId], queryFn: () => getMedia(g.mediaId), staleTime: 30_000 })),
  });
  const mediaById = new Map<string, Media | undefined>(groups.map((g, i) => [g.mediaId, medias[i]?.data]));

  const search = (text: string) => {
    const value = text.trim();
    if (value.length < MIN_QUERY_LENGTH) return;
    setParams({ q: value });
    const next = [value, ...recent.filter((r) => r !== value)];
    setRecent(next.slice(0, 6));
    saveRecent(next);
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    search(input);
  };

  const removeRecent = (value: string) => {
    const next = recent.filter((r) => r !== value);
    setRecent(next);
    saveRecent(next);
  };

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 pb-12">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Busca</h1>
        <p className="text-slate-600">
          Pergunte com suas palavras: a busca encontra o trecho que trata do assunto, mesmo que ele tenha sido dito de outro jeito.
        </p>
      </header>

      <form onSubmit={onSubmit} role="search" className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            aria-label="Pergunta"
            placeholder="Ex.: em qual aula expliquei a regra da cadeia?"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="h-12 w-full rounded-xl border border-slate-300 bg-white pl-12 pr-4 text-base shadow-xs outline-hidden focus:border-amber-400 focus:ring-2 focus:ring-amber-200"
          />
        </div>
        <Button type="submit" size="lg" className="h-12" disabled={input.trim().length < MIN_QUERY_LENGTH || isFetching}>
          {isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
          Buscar
        </Button>
      </form>

      {!query && <StartHints recent={recent} onPick={search} onRemove={removeRecent} />}

      {isFetching && <LoadingResults />}
      {isError && !isFetching && (
        <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Não foi possível fazer a busca agora. Tente de novo em instantes.
        </p>
      )}

      {!isFetching && data && (
        data.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-slate-300 px-6 py-12 text-center">
            <SearchX className="h-8 w-8 text-slate-400" />
            <p className="font-medium text-slate-900">Nenhum trecho das suas mídias trata disso.</p>
            <p className="max-w-md text-sm text-slate-500">
              Tente outras palavras ou uma pergunta mais específica. Mídias ainda em processamento entram na busca quando a análise
              termina.
            </p>
          </div>
        ) : (
          <section aria-label="Resultados" className="space-y-4">
            {/* O reranqueador não reconheceu nenhum trecho. Os mais próximos
                continuam na lista: com outras palavras, o trecho certo também
                pode receber nota baixa. */}
            {data.every((r) => r.match === "unrecognized") && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="status">
                <p className="font-medium">Nenhum trecho trata claramente disso.</p>
                <p className="mt-1">
                  Estes são os mais próximos; confira se algum responde. Se não, tente outras palavras ou uma pergunta mais específica.
                </p>
              </div>
            )}
            <p className="text-sm text-slate-500" aria-live="polite">
              {data.length} {data.length === 1 ? "trecho" : "trechos"} em {groups.length} {groups.length === 1 ? "mídia" : "mídias"}
            </p>
            {groups.map((group) => (
              <MediaResults key={group.mediaId} group={group} media={mediaById.get(group.mediaId)} query={query} />
            ))}
          </section>
        )
      )}
    </div>
  );
};

const MediaResults = ({ group, media, query }: { group: Group; media?: Media; query: string }) => {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? group.results : group.results.slice(0, 3);
  const title = group.title || media?.filename || "Mídia";
  return (
    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <header className="flex items-start gap-3 border-b border-slate-100 px-5 py-4">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
          {(media && TYPE_ICON[media.media_type]) ?? <FileText className="h-4 w-4" />}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold leading-snug text-slate-950">
            <Link to={`/media/${group.mediaId}`} className="hover:underline">
              {title}
            </Link>
          </h2>
          {media?.filename && title !== media.filename && <p className="truncate text-xs text-slate-500">{media.filename}</p>}
        </div>
      </header>
      <ol className="divide-y divide-slate-100">
        {visible.map((result, index) => {
          const match = result.match ? MATCH[result.match] : null;
          const start = formatTimestamp(result.start);
          const href = `/media/${result.media_id}${result.start != null ? `?t=${Math.floor(result.start)}&aba=transcricao` : ""}`;
          return (
            <li key={index} className="px-5 py-4">
              <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
                {start && (
                  <span className="inline-flex items-center gap-1 font-mono tabular-nums text-slate-500">
                    <Clock className="h-3 w-3" /> {start}
                    {result.end != null && ` – ${formatTimestamp(result.end)}`}
                  </span>
                )}
                {match && <span className={cn("rounded-full px-2 py-0.5 font-medium", match.className)}>{match.label}</span>}
              </div>
              <p className="text-[15px] leading-7 text-slate-700">{highlight(result.content, query)}</p>
              <Link
                to={href}
                className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-amber-700 underline-offset-2 hover:underline"
              >
                <PlayCircle className="h-4 w-4" /> {result.start != null ? "Abrir neste momento" : "Abrir a mídia"}
              </Link>
            </li>
          );
        })}
      </ol>
      {group.results.length > 3 && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="w-full border-t border-slate-100 px-5 py-2.5 text-left text-sm text-slate-600 hover:bg-slate-50"
        >
          {expanded ? "Mostrar menos" : `Mais ${group.results.length - 3} trechos desta mídia`}
        </button>
      )}
    </article>
  );
};

const StartHints = ({
  recent,
  onPick,
  onRemove,
}: {
  recent: string[];
  onPick: (q: string) => void;
  onRemove: (q: string) => void;
}) => (
  <div className="space-y-5">
    {recent.length > 0 && (
      <section>
        <h2 className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-700">
          <History className="h-4 w-4" /> Buscas recentes
        </h2>
        <ul className="flex flex-wrap gap-2">
          {recent.map((q) => (
            <li key={q} className="flex items-center rounded-full border border-slate-200 bg-white text-sm">
              <button type="button" onClick={() => onPick(q)} className="py-1 pl-3 pr-1 text-slate-700 hover:text-slate-950">
                {q}
              </button>
              <button type="button" onClick={() => onRemove(q)} aria-label={`Esquecer "${q}"`} className="rounded-full p-1.5 text-slate-400 hover:text-slate-700">
                <X className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      </section>
    )}
    <section className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">
      <h2 className="mb-2 font-medium text-slate-900">Como buscar</h2>
      <ul className="list-disc space-y-1 pl-5">
        <li>Faça uma pergunta ou descreva o assunto: não precisa acertar as palavras ditas.</li>
        <li>A busca olha só as suas mídias já analisadas, em vídeos, áudios e documentos.</li>
        <li>Cada resultado abre a mídia no momento do trecho.</li>
      </ul>
      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => onPick(example)}
            className="rounded-full bg-slate-100 px-3 py-1 text-slate-700 hover:bg-slate-200"
          >
            {example}
          </button>
        ))}
      </div>
    </section>
  </div>
);

const LoadingResults = () => (
  <div className="space-y-3" aria-live="polite">
    <p className="flex items-center gap-2 text-sm text-slate-500">
      <Loader2 className="h-4 w-4 animate-spin" /> Comparando a pergunta com os trechos das suas mídias...
    </p>
    {[0, 1].map((i) => (
      <div key={i} className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    ))}
  </div>
);

export default SearchPage;
