import { cn } from "@/lib/utils";
import { formatClock } from "@/lib/time";
import type { TextAnalysisResponse } from "@/types";
import { toneCounts } from "@/features/media/lib/analysisContent";

const TONES = [
  { key: "negative", label: "Negativo", bar: "bg-rose-400", dot: "bg-rose-400" },
  { key: "neutral", label: "Neutro", bar: "bg-slate-300", dot: "bg-slate-300" },
  { key: "positive", label: "Positivo", bar: "bg-emerald-400", dot: "bg-emerald-400" },
] as const;

const TONE_BY_LABEL: Record<string, (typeof TONES)[number]> = Object.fromEntries(TONES.map((t) => [t.key, t]));

/**
 * Tom dos trechos: a distribuição real (e não só o rótulo predominante, que
 * fazia um ensaio crítico parecer "64% negativo") e, em gravações, o tom ao
 * longo do tempo, com um clique levando ao trecho.
 */
export const SentimentResultPanel = ({
  analysis,
  onSeek,
  compact = false,
}: {
  analysis: TextAnalysisResponse | null | undefined;
  onSeek?: (time: number) => void;
  /** Só a barra e a linha do tempo (coluna do reprodutor). */
  compact?: boolean;
}) => {
  if (!analysis) return null;
  const counts = toneCounts(analysis);
  // Sem trechos classificados: o fator foi desligado (ANALYSIS_FACTORS) ou falhou. Não é "Neutro".
  if (!counts.total) {
    return compact ? null : <p className="text-sm text-muted-foreground">O tom não foi analisado nesta mídia.</p>;
  }
  const items = analysis.sentiment_items ?? [];
  const timed = items.filter((i) => i.start != null).sort((a, b) => (a.start ?? 0) - (b.start ?? 0));
  const predominant = TONE_BY_LABEL[String(analysis.overall_sentiment).toLowerCase()];

  return (
    <section aria-label="Tom do conteúdo" className={cn(!compact && "space-y-4")}>
      {!compact && (
        <p className="text-sm text-slate-700">
          Tom predominante: <strong className="font-semibold">{predominant?.label ?? "Neutro"}</strong>, em {counts.total} trechos
          classificados automaticamente.
        </p>
      )}
      <div className="flex h-2.5 overflow-hidden rounded-full bg-slate-100" role="img" aria-label={TONES.map((t) => `${counts[t.key]} ${t.label.toLowerCase()}`).join(", ")}>
        {TONES.map((t) => (
          <div key={t.key} className={t.bar} style={{ width: `${(counts[t.key] / counts.total) * 100}%` }} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
        {TONES.map((t) => (
          <span key={t.key} className="inline-flex items-center gap-1.5">
            <span className={cn("h-2 w-2 rounded-full", t.dot)} /> {t.label} {counts[t.key]}
          </span>
        ))}
      </div>

      {timed.length > 1 && (
        <div className={cn(compact ? "mt-3" : "")}>
          {!compact && <p className="mb-1 text-xs text-slate-500">Ao longo da gravação</p>}
          <div className="flex h-5 gap-px overflow-hidden rounded" aria-hidden={!onSeek}>
            {timed.map((item) => {
              const tone = TONE_BY_LABEL[String(item.label).toLowerCase()] ?? TONES[1];
              return (
                <button
                  key={item.chunk_id}
                  type="button"
                  tabIndex={onSeek ? 0 : -1}
                  disabled={!onSeek}
                  onClick={() => onSeek?.(item.start ?? 0)}
                  title={`${formatClock(item.start)} · ${tone.label}`}
                  aria-label={`${tone.label} em ${formatClock(item.start)}`}
                  className={cn("h-full flex-1 opacity-80 hover:opacity-100", tone.bar)}
                />
              );
            })}
          </div>
        </div>
      )}

      {!compact && (
        <p className="text-xs text-muted-foreground">
          O modelo foi treinado com redes sociais: em aulas e ensaios, "negativo" costuma indicar crítica ou alerta, não
          emoção.
        </p>
      )}
    </section>
  );
};
