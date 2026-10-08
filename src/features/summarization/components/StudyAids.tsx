import { useState } from "react";
import { toast } from "react-toastify";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, Edit3, Eye, EyeOff, Plus, Save, Shuffle, Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiErrorMessage } from "@/lib/errors";
import { formatClock, parseClock } from "@/lib/time";
import { cn } from "@/lib/utils";
import type { TextAnalysisResponse } from "@/types";
import { chaptersOf, questionsOf, type Chapter, type ReviewQuestion } from "@/features/media/lib/analysisContent";
import { correctStudyAids } from "../api";

export type { Chapter, ReviewQuestion };

export const TimeLink = ({ seconds, onSeek }: { seconds: number; onSeek?: (time: number) => void }) =>
  onSeek ? (
    <button
      type="button"
      onClick={() => onSeek(seconds)}
      className="rounded font-mono text-xs tabular-nums text-amber-700 underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
      aria-label={`Ir para ${formatClock(seconds)}`}
    >
      {formatClock(seconds)}
    </button>
  ) : (
    <span className="font-mono text-xs tabular-nums text-slate-500">{formatClock(seconds)}</span>
  );

/**
 * Perguntas de revisão (respostas escondidas até o estudante pedir, ou uma
 * de cada vez no modo "testar-me") e a correção de capítulos e perguntas.
 */
export const StudyAids = ({
  analysis,
  onSeek,
  canEdit = true,
}: {
  analysis: TextAnalysisResponse | null | undefined;
  onSeek?: (time: number) => void;
  canEdit?: boolean;
}) => {
  const chapters = chaptersOf(analysis);
  const questions = questionsOf(analysis);
  const [shown, setShown] = useState<Set<number>>(new Set());
  const [quiz, setQuiz] = useState<number | null>(null);
  const [editing, setEditing] = useState(false);

  if (!analysis) return null;
  if (editing) {
    return <StudyAidsEditor analysis={analysis} chapters={chapters} questions={questions} onClose={() => setEditing(false)} />;
  }
  if (!chapters.length && !questions.length) {
    return <p className="text-sm text-muted-foreground">Esta mídia não tem capítulos nem perguntas de revisão (gravação curta ou documento).</p>;
  }

  const toggle = (index: number) =>
    setShown((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          <BookOpen className="h-4 w-4 text-amber-600" /> Perguntas de revisão
        </h3>
        <div className="flex gap-2">
          {questions.length > 1 && (
            <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setQuiz(quiz === null ? 0 : null)}>
              <Shuffle className="h-3.5 w-3.5" /> {quiz === null ? "Testar-me" : "Ver todas"}
            </Button>
          )}
          {canEdit && (
            <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setEditing(true)}>
              <Edit3 className="h-3.5 w-3.5" /> Editar capítulos e perguntas
            </Button>
          )}
        </div>
      </div>

      {quiz !== null && questions[quiz] ? (
        <QuizCard
          index={quiz}
          total={questions.length}
          item={questions[quiz]}
          onSeek={onSeek}
          onNext={() => setQuiz((quiz + 1) % questions.length)}
        />
      ) : (
        <ol className="space-y-3">
          {questions.map((item, index) => (
            <li key={index} className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="flex gap-3 text-[15px] font-medium text-slate-900">
                <span className="tabular-nums text-amber-600">{index + 1}.</span>
                <span>{item.question}</span>
              </p>
              {shown.has(index) ? (
                <div className="mt-2 flex flex-wrap items-baseline gap-2 pl-6 text-sm text-slate-700">
                  <span>{item.answer}</span>
                  {item.start != null && <TimeLink seconds={item.start} onSeek={onSeek} />}
                  <button type="button" onClick={() => toggle(index)} className="text-xs text-slate-400 hover:text-slate-600">
                    <EyeOff className="inline h-3.5 w-3.5" /> esconder
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => toggle(index)}
                  className="mt-2 inline-flex items-center gap-1 pl-6 text-sm text-amber-700 underline-offset-2 hover:underline"
                >
                  <Eye className="h-3.5 w-3.5" /> Mostrar resposta
                </button>
              )}
            </li>
          ))}
        </ol>
      )}
      {questions.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Perguntas geradas automaticamente a partir do conteúdo; confira as respostas no trecho indicado.
        </p>
      )}
    </div>
  );
};

const QuizCard = ({
  index,
  total,
  item,
  onSeek,
  onNext,
}: {
  index: number;
  total: number;
  item: ReviewQuestion;
  onSeek?: (time: number) => void;
  onNext: () => void;
}) => {
  const [revealed, setRevealed] = useState(false);
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-6" aria-live="polite">
      <p className="text-xs font-medium uppercase tracking-wide text-amber-700">
        Pergunta {index + 1} de {total}
      </p>
      <p className="mt-2 text-lg font-medium text-slate-900">{item.question}</p>
      {revealed ? (
        <p className="mt-4 text-slate-700">
          {item.answer} {item.start != null && <TimeLink seconds={item.start} onSeek={onSeek} />}
        </p>
      ) : (
        <p className="mt-4 text-sm text-slate-500">Pense na resposta antes de revelar.</p>
      )}
      <div className="mt-5 flex gap-2">
        {!revealed && (
          <Button size="sm" onClick={() => setRevealed(true)}>
            Revelar resposta
          </Button>
        )}
        <Button
          size="sm"
          variant={revealed ? "default" : "outline"}
          onClick={() => {
            setRevealed(false);
            onNext();
          }}
        >
          Próxima pergunta
        </Button>
      </div>
    </div>
  );
};

type QuestionDraft = { question: string; answer: string; time: string };

const StudyAidsEditor = ({
  analysis,
  chapters,
  questions,
  onClose,
}: {
  analysis: TextAnalysisResponse;
  chapters: Chapter[];
  questions: ReviewQuestion[];
  onClose: () => void;
}) => {
  const queryClient = useQueryClient();
  const [chapterTitles, setChapterTitles] = useState(chapters.map((c) => c.title));
  const [drafts, setDrafts] = useState<QuestionDraft[]>(
    questions.map((q) => ({ question: q.question, answer: q.answer, time: q.start != null ? formatClock(q.start) : "" })),
  );
  const [saving, setSaving] = useState(false);

  const incomplete =
    chapterTitles.some((t) => !t.trim()) ||
    drafts.some((d) => !d.question.trim() || !d.answer.trim() || (d.time.trim() && parseClock(d.time) === null));

  const updateDraft = (index: number, change: Partial<QuestionDraft>) =>
    setDrafts((current) => current.map((d, i) => (i === index ? { ...d, ...change } : d)));

  const save = async () => {
    setSaving(true);
    try {
      await correctStudyAids(analysis.analysis_id, {
        chapters: chapters.map((c, i) => ({ start: c.start, end: c.end, title: chapterTitles[i].trim() })),
        review_questions: drafts.map((d) => ({
          question: d.question.trim(),
          answer: d.answer.trim(),
          start: d.time.trim() ? parseClock(d.time) : null,
        })),
      });
      await queryClient.invalidateQueries({ queryKey: ["text-analysis"] });
      toast.success("Capítulos e perguntas salvos. A versão da IA continua guardada.");
      onClose();
    } catch (err) {
      toast.error(apiErrorMessage(err, "Não foi possível salvar as alterações."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {chapters.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-base font-semibold text-slate-900">Títulos dos capítulos</h3>
          {chapters.map((chapter, index) => (
            <label key={index} className="flex items-center gap-3">
              <span className="w-14 shrink-0 font-mono text-xs tabular-nums text-slate-500">{formatClock(chapter.start)}</span>
              <Input
                aria-label={`Título do capítulo ${index + 1}`}
                value={chapterTitles[index]}
                onChange={(e) => setChapterTitles((t) => t.map((v, i) => (i === index ? e.target.value : v)))}
              />
            </label>
          ))}
        </section>
      )}

      <section className="space-y-3">
        <h3 className="text-base font-semibold text-slate-900">Perguntas de revisão</h3>
        {drafts.map((draft, index) => (
          <div key={index} className="space-y-2 rounded-xl border border-slate-200 p-3">
            <div className="flex items-start gap-2">
              <span className="pt-2 text-sm tabular-nums text-amber-600">{index + 1}.</span>
              <Input
                aria-label={`Pergunta ${index + 1}`}
                placeholder="Pergunta"
                value={draft.question}
                onChange={(e) => updateDraft(index, { question: e.target.value })}
              />
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Remover pergunta ${index + 1}`}
                onClick={() => setDrafts((d) => d.filter((_, i) => i !== index))}
              >
                <Trash2 className="h-4 w-4 text-slate-500" />
              </Button>
            </div>
            <div className="flex gap-2 pl-5">
              <Input
                aria-label={`Resposta ${index + 1}`}
                placeholder="Resposta"
                value={draft.answer}
                onChange={(e) => updateDraft(index, { answer: e.target.value })}
              />
              <Input
                aria-label={`Momento da resposta ${index + 1}`}
                placeholder="mm:ss"
                value={draft.time}
                onChange={(e) => updateDraft(index, { time: e.target.value })}
                className={cn("w-24 font-mono", draft.time.trim() && parseClock(draft.time) === null && "border-red-400")}
              />
            </div>
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => setDrafts((d) => [...d, { question: "", answer: "", time: "" }])}
        >
          <Plus className="h-3.5 w-3.5" /> Adicionar pergunta
        </Button>
      </section>

      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        <Button variant="ghost" size="sm" onClick={onClose} disabled={saving}>
          <X className="mr-1 h-4 w-4" /> Cancelar
        </Button>
        <Button size="sm" onClick={save} disabled={saving || incomplete}>
          <Save className="mr-1 h-4 w-4" /> {saving ? "Salvando..." : "Salvar"}
        </Button>
      </div>
    </div>
  );
};
