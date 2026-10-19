import * as React from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Check, Eye, PlayCircle, Shuffle, X } from "lucide-react";
import { toast } from "react-toastify";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/Select";
import { useMediaNames } from "@/features/media/hooks/useMediaNames";
import { answerReviewQuestion, getStudyDeck, type StudyQuestion } from "@/features/summarization/api";
import { progressSummary } from "@/features/summarization/studyProgress";
import { apiErrorMessage } from "@/lib/errors";
import { formatClock } from "@/lib/time";
import { cn } from "@/lib/utils";

type StudyCard = StudyQuestion & { key: string; analysisId: string; mediaId: string | null };
type Mode = "due" | "all";

const shuffled = <T,>(items: T[]): T[] => {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
};

/** Situação da pergunta, em palavras: nova, dominada ou quando revê-la. */
const statusOf = (card: StudyCard): { label: string; tone: string } => {
  const p = card.progress;
  if (!p) return { label: "Nova", tone: "bg-slate-100 text-slate-700" };
  if (p.mastered) return { label: "Dominada", tone: "bg-emerald-100 text-emerald-800" };
  if (card.due) return { label: "Revisar agora", tone: "bg-amber-100 text-amber-800" };
  const when = p.due_at ? formatDistanceToNow(new Date(p.due_at), { addSuffix: true, locale: ptBR }) : "";
  return { label: `Revisar ${when}`, tone: "bg-sky-100 text-sky-800" };
};

const QuestionCard = ({ card, mediaName }: { card: StudyCard; mediaName: string }) => {
  const [open, setOpen] = React.useState(false);
  const queryClient = useQueryClient();
  const answer = useMutation({
    mutationFn: (correct: boolean) => answerReviewQuestion(card.analysisId, card.question, correct),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["study-deck"] }),
    onError: (error) => toast.error(apiErrorMessage(error, "Não foi possível registrar a resposta.")),
  });
  const status = statusOf(card);

  return (
    <li className="flex flex-col rounded-xl border border-[#ede4d5] bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="min-w-0 text-xs text-muted-foreground wrap-anywhere">{mediaName}</p>
        <span className={cn("shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium", status.tone)}>
          {status.label}
        </span>
      </div>
      <p className="mt-1 font-medium text-slate-900">{card.question}</p>
      {open ? (
        <>
          <div className="mt-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-800">
            <p>{card.answer}</p>
            {card.mediaId && card.start != null && (
              <Link
                to={`/media/${card.mediaId}?t=${Math.floor(card.start)}`}
                className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-slate-900 hover:underline"
              >
                <PlayCircle className="h-3.5 w-3.5" />
                Ver na gravação ({formatClock(card.start)})
              </Link>
            )}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Você tinha acertado?</p>
          <div className="mt-1 flex gap-2">
            <Button variant="outline" size="sm" disabled={answer.isPending} onClick={() => answer.mutate(false)}>
              <X className="mr-1.5 h-4 w-4 text-rose-600" />
              Errei
            </Button>
            <Button variant="outline" size="sm" disabled={answer.isPending} onClick={() => answer.mutate(true)}>
              <Check className="mr-1.5 h-4 w-4 text-emerald-600" />
              Acertei
            </Button>
          </div>
        </>
      ) : (
        <Button variant="ghost" size="sm" className="mt-2 -ml-2 self-start" onClick={() => setOpen(true)}>
          <Eye className="mr-2 h-4 w-4" />
          Mostrar resposta
        </Button>
      )}
    </li>
  );
};

const Stat = ({ label, value, detail }: { label: string; value: string; detail: string }) => (
  <Card className="border-[#ede4d5] p-3 sm:p-4">
    <p className="text-xs font-medium text-muted-foreground sm:text-sm">{label}</p>
    <p className="mt-1 text-2xl font-semibold sm:text-3xl">{value}</p>
    <p className="mt-1 hidden text-xs text-muted-foreground sm:block">{detail}</p>
  </Card>
);

/**
 * Revisão de estudo: as perguntas de todas as mídias, com revisão espaçada.
 * Acertar afasta a próxima revisão (1, 3, 7, 14 dias); errar traz a pergunta
 * de volta hoje. "Para revisar" mostra só o que está na hora.
 */
const StudyPage = () => {
  const deck = useQuery({ queryKey: ["study-deck"], queryFn: getStudyDeck });
  const nameOf = useMediaNames();
  const [mode, setMode] = React.useState<Mode>("due");
  const [mediaFilter, setMediaFilter] = React.useState("all");
  const [order, setOrder] = React.useState(0); // muda a cada "Embaralhar"

  const entries = React.useMemo(() => deck.data ?? [], [deck.data]);
  const summary = React.useMemo(() => progressSummary(entries), [entries]);
  const cards = React.useMemo(() => {
    const all: StudyCard[] = entries.flatMap((entry) =>
      entry.questions.map((q, i) => ({ ...q, key: `${entry.analysis_id}-${i}`, analysisId: entry.analysis_id, mediaId: entry.media_id })),
    );
    const filtered = all.filter((c) => (mediaFilter === "all" || c.mediaId === mediaFilter) && (mode === "all" || c.due));
    return order ? shuffled(filtered) : filtered;
  }, [entries, mediaFilter, mode, order]);

  if (deck.isError) {
    return <ErrorState title="Não foi possível carregar as perguntas" message="Tente novamente em instantes." onRetry={() => deck.refetch()} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Revisão</h1>
        <p className="text-sm text-muted-foreground">
          Responda de cabeça, abra a resposta e marque se acertou: o que você erra volta mais vezes.
        </p>
      </div>

      {deck.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : summary.total === 0 ? (
        <Card className="border-[#ede4d5] p-8 text-center">
          <p className="font-medium text-slate-900">Nenhuma pergunta de revisão ainda</p>
          <p className="mt-1 text-sm text-muted-foreground">
            As perguntas são geradas na análise de cada mídia. Envie uma aula ou palestra para começar.
          </p>
          <Button asChild className="mt-4">
            <Link to="/upload">Enviar mídia</Link>
          </Button>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
            <Stat label="Para revisar" value={String(summary.due)} detail="Novas e as que chegaram na hora" />
            <Stat label="Dominadas" value={`${summary.mastered}`} detail={`de ${summary.total} perguntas`} />
            <Stat label="Aprendendo" value={`${summary.learning}`} detail={`${summary.fresh} ainda não respondidas`} />
            <Stat
              label="Acertos"
              value={summary.accuracy === null ? "—" : `${summary.accuracy}%`}
              detail="De todas as respostas marcadas"
            />
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex gap-2" role="group" aria-label="Quais perguntas">
              {(
                [
                  ["due", `Para revisar (${summary.due})`],
                  ["all", `Todas (${summary.total})`],
                ] as [Mode, string][]
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={mode === value}
                  onClick={() => setMode(value)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-sm",
                    mode === value ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 text-slate-700 hover:border-slate-400",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Select value={mediaFilter} onValueChange={setMediaFilter}>
                <SelectTrigger className="w-full sm:w-64" aria-label="Mídia">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas as mídias</SelectItem>
                  {entries
                    .filter((e) => e.media_id)
                    .map((entry) => (
                      <SelectItem key={entry.analysis_id} value={entry.media_id!}>
                        {nameOf(entry.media_id)} ({entry.questions.length})
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={() => setOrder((n) => n + 1)} disabled={cards.length < 2}>
                <Shuffle className="mr-2 h-4 w-4" />
                Embaralhar
              </Button>
            </div>
          </div>

          {cards.length === 0 ? (
            <Card className="border-[#ede4d5] p-8 text-center">
              <p className="font-medium text-slate-900">Nada para revisar agora</p>
              <p className="mt-1 text-sm text-muted-foreground">
                As perguntas que você acertou voltam nos próximos dias. Veja todas, se quiser praticar mais.
              </p>
              <Button variant="outline" className="mt-4" onClick={() => setMode("all")}>
                Ver todas as perguntas
              </Button>
            </Card>
          ) : (
            <ul className="grid gap-3 md:grid-cols-2">
              {cards.map((card) => (
                <QuestionCard key={`${card.key}-${order}`} card={card} mediaName={nameOf(card.mediaId)} />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
};

export default StudyPage;
