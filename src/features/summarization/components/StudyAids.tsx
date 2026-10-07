import { useState } from "react";
import { BookOpen, ListOrdered } from "lucide-react";

export type Chapter = { start: number; end: number; title: string };
export type ReviewQuestion = { question: string; answer: string; start: number | null };

const formatTime = (seconds: number) => {
  const s = Math.floor(seconds);
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return s >= 3600 ? `${Math.floor(s / 3600)}:${mm}:${ss}` : `${mm}:${ss}`;
};

const TimeLink = ({ seconds, onSeek }: { seconds: number; onSeek?: (time: number) => void }) =>
  onSeek ? (
    <button
      type="button"
      onClick={() => onSeek(seconds)}
      className="font-mono text-xs text-amber-700 underline-offset-2 hover:underline"
      aria-label={`Ir para ${formatTime(seconds)}`}
    >
      {formatTime(seconds)}
    </button>
  ) : (
    <span className="font-mono text-xs text-slate-500">{formatTime(seconds)}</span>
  );

/**
 * Capítulos da gravação e perguntas de revisão (diagnostics.chapters e
 * diagnostics.review_questions). Os horários levam o reprodutor ao momento;
 * as respostas ficam escondidas até o estudante pedir.
 */
export const StudyAids = ({
  chapters = [],
  questions = [],
  onSeek,
}: {
  chapters?: Chapter[];
  questions?: ReviewQuestion[];
  onSeek?: (time: number) => void;
}) => {
  const [shown, setShown] = useState<Set<number>>(new Set());
  if (!chapters.length && !questions.length) return null;

  const toggle = (index: number) =>
    setShown((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });

  return (
    <div className="space-y-4">
      {chapters.length > 0 && (
        <section aria-labelledby="chapters-title" className="rounded-xl border border-[#ede4d5] bg-white p-4">
          <h3 id="chapters-title" className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <ListOrdered className="h-4 w-4 text-amber-600" /> Capítulos
          </h3>
          <ol className="space-y-1 text-sm">
            {chapters.map((chapter, index) => (
              <li key={index} className="flex items-baseline gap-3">
                <TimeLink seconds={chapter.start} onSeek={onSeek} />
                <span>{chapter.title}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
      {questions.length > 0 && (
        <section aria-labelledby="questions-title" className="rounded-xl border border-[#ede4d5] bg-white p-4">
          <h3 id="questions-title" className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <BookOpen className="h-4 w-4 text-amber-600" /> Perguntas de revisão
          </h3>
          <ol className="list-decimal space-y-3 pl-5 text-sm">
            {questions.map((item, index) => (
              <li key={index}>
                <p>{item.question}</p>
                {shown.has(index) ? (
                  <p className="mt-1 text-slate-700">
                    {item.answer} {item.start != null && <TimeLink seconds={item.start} onSeek={onSeek} />}
                  </p>
                ) : (
                  <button
                    type="button"
                    onClick={() => toggle(index)}
                    className="mt-1 text-xs text-amber-700 underline-offset-2 hover:underline"
                  >
                    Ver resposta
                  </button>
                )}
              </li>
            ))}
          </ol>
          <p className="mt-3 text-[11px] text-muted-foreground">
            Perguntas geradas automaticamente a partir do conteúdo; confira as respostas no trecho indicado.
          </p>
        </section>
      )}
    </div>
  );
};
