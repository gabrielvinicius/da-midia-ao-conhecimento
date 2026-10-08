import * as React from "react";
import { Check, Edit3, Search, X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatClock } from "@/lib/time";
import { cn } from "@/lib/utils";
import { TranscriptionStatus, type Transcription, type TranscriptionSegment } from "@/types";
import { useCorrectSegment } from "../hooks/useTranscriptionMutations";
import { EditSpeakersDialog } from "./EditSpeakersDialog";

interface InteractiveTranscriptionPanelProps {
  transcription: Transcription | null | undefined;
  isLoading?: boolean;
  currentTime: number;
  onSeek?: (time: number) => void;
  /** Só o dono ou um administrador corrige. */
  canEdit?: boolean;
}

const SPEAKER_COLORS = ["text-sky-600", "text-emerald-600", "text-amber-600", "text-indigo-600", "text-rose-600", "text-cyan-600"];

const normalize = (text: string) => text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Destaca as ocorrências da busca (sem diferenciar acentos e maiúsculas). */
const highlight = (text: string, query: string) => {
  if (!query) return text;
  const haystack = normalize(text);
  const needle = normalize(query);
  const parts: React.ReactNode[] = [];
  let from = 0;
  let at = haystack.indexOf(needle);
  while (at >= 0) {
    parts.push(text.slice(from, at), <mark key={at} className="rounded bg-amber-200 px-0.5">{text.slice(at, at + needle.length)}</mark>);
    from = at + needle.length;
    at = haystack.indexOf(needle, from);
  }
  parts.push(text.slice(from));
  return parts;
};

/**
 * Transcrição com o horário de cada trecho: o trecho em reprodução fica
 * destacado e acompanha o vídeo, um clique leva o vídeo ao trecho, a busca
 * filtra os trechos, e cada trecho pode ser corrigido (o texto do modelo
 * fica guardado; a próxima análise usa a correção).
 */
export const InteractiveTranscriptionPanel = ({
  transcription,
  isLoading,
  currentTime,
  onSeek,
  canEdit = true,
}: InteractiveTranscriptionPanelProps) => {
  const [query, setQuery] = React.useState("");
  const [editing, setEditing] = React.useState<number | null>(null);
  const [draft, setDraft] = React.useState("");
  const [follow, setFollow] = React.useState(true);
  const listRef = React.useRef<HTMLOListElement>(null);
  const correct = useCorrectSegment();

  const segments = React.useMemo(() => transcription?.segments ?? [], [transcription]);
  const speakerColor = React.useMemo(() => {
    const map: Record<string, string> = {};
    segments.forEach((s) => {
      if (s.speaker && !map[s.speaker]) map[s.speaker] = SPEAKER_COLORS[Object.keys(map).length % SPEAKER_COLORS.length];
    });
    return map;
  }, [segments]);
  const activeIndex = segments.findIndex((s) => currentTime >= s.start && currentTime < s.end);

  // Acompanha o vídeo rolando só a lista (antes, a página inteira pulava).
  React.useEffect(() => {
    const list = listRef.current;
    if (!follow || query || editing !== null || activeIndex < 0 || !list) return;
    const item = list.querySelector<HTMLElement>(`[data-index="${activeIndex}"]`);
    if (item && (item.offsetTop < list.scrollTop || item.offsetTop > list.scrollTop + list.clientHeight - 80)) {
      const top = item.offsetTop - 16;
      if (typeof list.scrollTo === "function") list.scrollTo({ top, behavior: "smooth" });
      else list.scrollTop = top;
    }
  }, [activeIndex, follow, query, editing]);

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (!transcription) return <p className="text-sm text-muted-foreground">Transcrição indisponível.</p>;
  if (transcription.status !== TranscriptionStatus.COMPLETED) {
    return <p className="text-sm text-muted-foreground">A transcrição aparece aqui quando o processamento terminar.</p>;
  }

  const visible = segments
    .map((segment, index) => ({ segment, index }))
    .filter(({ segment }) => !query || normalize(segment.text).includes(normalize(query)));
  const isDiarized = segments.some((s) => s.speaker);

  const startEditing = (index: number, segment: TranscriptionSegment) => {
    setEditing(index);
    setDraft(segment.text.trim());
  };

  const save = (index: number) => {
    if (!draft.trim()) return;
    correct.mutate(
      { transcriptionId: transcription.id, index, text: draft },
      { onSuccess: () => setEditing(null) },
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[12rem] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar na transcrição"
            aria-label="Buscar na transcrição"
            className="h-9 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        {onSeek && (
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} className="accent-amber-600" />
            Acompanhar o vídeo
          </label>
        )}
        {isDiarized && <EditSpeakersDialog transcription={transcription} />}
      </div>
      <p className="text-xs text-muted-foreground" aria-live="polite">
        {query
          ? `${visible.length} de ${segments.length} trechos com "${query}".`
          : `${segments.length} trechos${transcription.corrected_segments ? ` · ${transcription.corrected_segments} corrigidos por você` : ""}${canEdit ? " · use o lápis ao lado de um trecho para corrigi-lo" : ""}.`}
      </p>

      {segments.length === 0 ? (
        <p className="whitespace-pre-wrap text-[15px] leading-7 text-slate-800">{transcription.text}</p>
      ) : (
        <ol ref={listRef} className="relative max-h-[65vh] space-y-1 overflow-y-auto pr-1" aria-label="Trechos da transcrição">
          {visible.map(({ segment, index }) => {
            const isActive = index === activeIndex;
            const label = segment.speaker ? transcription.speaker_aliases?.[segment.speaker] || segment.speaker : null;
            return (
              <li
                key={index}
                data-index={index}
                className={cn(
                  "group flex gap-3 rounded-lg px-2 py-2 transition-colors",
                  isActive ? "bg-amber-50 ring-1 ring-amber-200" : "hover:bg-slate-50",
                )}
              >
                <button
                  type="button"
                  onClick={() => onSeek?.(segment.start)}
                  disabled={!onSeek}
                  className="mt-1 w-12 shrink-0 self-start text-left font-mono text-xs tabular-nums text-slate-500 hover:text-amber-700 disabled:hover:text-slate-500"
                  aria-label={`Ir para ${formatClock(segment.start)}`}
                >
                  {formatClock(segment.start)}
                </button>
                {editing === index ? (
                  <div className="flex-1 space-y-2">
                    <textarea
                      aria-label={`Texto do trecho de ${formatClock(segment.start)}`}
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      rows={Math.min(6, Math.max(2, Math.ceil(draft.length / 80)))}
                      className="w-full rounded-lg border border-slate-300 p-2 text-[15px] leading-7 outline-none focus:ring-2 focus:ring-primary/20"
                      autoFocus
                    />
                    {segment.original_text && (
                      <p className="text-xs text-slate-500">Texto da IA: {segment.original_text.trim()}</p>
                    )}
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => save(index)} disabled={correct.isPending || !draft.trim()} className="gap-1">
                        <Check className="h-3.5 w-3.5" /> Salvar
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditing(null)} disabled={correct.isPending} className="gap-1">
                        <X className="h-3.5 w-3.5" /> Cancelar
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className={cn("flex-1 text-[15px] leading-7", isActive ? "text-slate-950" : "text-slate-700")}>
                      {label && <span className={cn("mr-1 font-semibold", speakerColor[segment.speaker!])}>{label}:</span>}
                      {highlight(segment.text.trim(), query)}
                      {segment.original_text && (
                        <span className="ml-2 rounded bg-sky-50 px-1.5 py-0.5 text-[11px] text-sky-700" title={`Texto da IA: ${segment.original_text.trim()}`}>
                          corrigido
                        </span>
                      )}
                    </p>
                    {canEdit && (
                      <button
                        type="button"
                        onClick={() => startEditing(index, segment)}
                        aria-label={`Corrigir o trecho de ${formatClock(segment.start)}`}
                        className="mt-1 h-7 w-7 shrink-0 rounded-md text-slate-400 opacity-0 transition-opacity hover:bg-slate-100 hover:text-slate-700 focus-visible:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100"
                      >
                        <Edit3 className="mx-auto h-3.5 w-3.5" />
                      </button>
                    )}
                  </>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
};
