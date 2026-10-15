import { ListOrdered } from "lucide-react";

import { formatClock } from "@/lib/time";
import { cn } from "@/lib/utils";
import { activeChapterIndex, type Chapter } from "@/features/media/lib/analysisContent";

/**
 * Índice da gravação ao lado do reprodutor: o capítulo em reprodução fica
 * destacado, e cada capítulo leva o vídeo ao seu início.
 */
export const ChapterNav = ({
  chapters,
  currentTime,
  duration,
  onSeek,
}: {
  chapters: Chapter[];
  currentTime: number;
  duration?: number | null;
  onSeek?: (time: number) => void;
}) => {
  if (!chapters.length) return null;
  const active = activeChapterIndex(chapters, currentTime);
  const total = duration || chapters[chapters.length - 1].end || 1;

  return (
    <nav aria-label="Capítulos" className="rounded-2xl border border-slate-200 bg-white p-4">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
        <ListOrdered className="h-4 w-4 text-amber-600" /> Capítulos
      </h2>
      {/* Linha do tempo: a largura de cada capítulo é a sua duração. */}
      <div className="mb-3 flex h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden>
        {chapters.map((c, i) => (
          <div
            key={i}
            className={cn("h-full border-r border-white last:border-r-0", i === active ? "bg-amber-500" : "bg-slate-300")}
            style={{ width: `${(Math.max(0, c.end - c.start) / total) * 100}%` }}
          />
        ))}
      </div>
      <ol className="space-y-0.5">
        {chapters.map((chapter, index) => {
          const isActive = index === active;
          const content = (
            <>
              <span className={cn("w-12 shrink-0 font-mono text-xs tabular-nums", isActive ? "text-amber-700" : "text-slate-500")}>
                {formatClock(chapter.start)}
              </span>
              <span className={cn("text-sm leading-snug", isActive ? "font-medium text-slate-950" : "text-slate-700")}>
                {chapter.title}
              </span>
            </>
          );
          return (
            <li key={index}>
              {onSeek ? (
                <button
                  type="button"
                  onClick={() => onSeek(chapter.start)}
                  aria-current={isActive ? "true" : undefined}
                  className={cn(
                    "flex w-full items-baseline gap-2 rounded-lg px-2 py-1.5 text-left transition-colors",
                    "focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-amber-400",
                    isActive ? "bg-amber-50" : "hover:bg-slate-50",
                  )}
                >
                  {content}
                </button>
              ) : (
                <div className="flex items-baseline gap-2 px-2 py-1.5">{content}</div>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
