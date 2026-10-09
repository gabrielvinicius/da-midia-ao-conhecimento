import * as React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Eye, EyeOff, PlayCircle, Shuffle } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/Select";
import { listMedia } from "@/features/media/api";
import { getStudyDeck, type StudyQuestion } from "@/features/summarization/api";
import { formatClock } from "@/lib/time";

type StudyCard = StudyQuestion & { key: string; mediaId: string | null; mediaName: string };

const shuffled = <T,>(items: T[]): T[] => {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
};

const QuestionCard = ({ card, index }: { card: StudyCard; index: number }) => {
  const [open, setOpen] = React.useState(false);
  return (
    <li className="rounded-xl border border-[#ede4d5] bg-white p-4">
      <p className="text-xs text-muted-foreground [overflow-wrap:anywhere]">
        {index + 1}. {card.mediaName}
      </p>
      <p className="mt-1 font-medium text-slate-900">{card.question}</p>
      {open ? (
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
      ) : null}
      <Button variant="ghost" size="sm" className="mt-2 -ml-2" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        {open ? <EyeOff className="mr-2 h-4 w-4" /> : <Eye className="mr-2 h-4 w-4" />}
        {open ? "Esconder resposta" : "Mostrar resposta"}
      </Button>
    </li>
  );
};

/**
 * Revisão de estudo: as perguntas geradas em todas as mídias num lugar só.
 * Cada uma esconde a resposta até o aluno pedir e leva ao momento da
 * gravação onde ela aparece.
 */
const StudyPage = () => {
  const deck = useQuery({ queryKey: ["study-deck"], queryFn: getStudyDeck });
  const media = useQuery({ queryKey: ["media-names"], queryFn: () => listMedia(1, 100), staleTime: 60_000 });
  const [mediaFilter, setMediaFilter] = React.useState("all");
  const [order, setOrder] = React.useState(0); // muda a cada "Embaralhar"

  const names = React.useMemo(
    () => new Map((media.data?.items ?? []).map((m) => [m.id, m.filename || "Mídia sem nome"])),
    [media.data],
  );
  const cards = React.useMemo(() => {
    const all: StudyCard[] = (deck.data ?? []).flatMap((entry) =>
      entry.questions.map((q, i) => ({
        ...q,
        key: `${entry.analysis_id}-${i}`,
        mediaId: entry.media_id,
        mediaName: (entry.media_id && names.get(entry.media_id)) || "Mídia",
      })),
    );
    const filtered = mediaFilter === "all" ? all : all.filter((c) => c.mediaId === mediaFilter);
    return order ? shuffled(filtered) : filtered;
  }, [deck.data, names, mediaFilter, order]);

  const mediaOptions = (deck.data ?? []).filter((e) => e.media_id);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Revisão</h1>
          <p className="text-sm text-muted-foreground">
            Perguntas sobre o conteúdo das suas mídias. Tente responder antes de abrir a resposta.
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={mediaFilter} onValueChange={setMediaFilter}>
            <SelectTrigger className="w-full sm:w-64" aria-label="Mídia">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas as mídias</SelectItem>
              {mediaOptions.map((entry) => (
                <SelectItem key={entry.analysis_id} value={entry.media_id!}>
                  {names.get(entry.media_id!) ?? "Mídia"} ({entry.questions.length})
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

      {deck.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : deck.isError ? (
        <ErrorState title="Não foi possível carregar as perguntas" message="Tente novamente em instantes." onRetry={() => deck.refetch()} />
      ) : cards.length === 0 ? (
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
          <p className="text-sm text-muted-foreground">
            {cards.length} {cards.length === 1 ? "pergunta" : "perguntas"}
          </p>
          <ul className="grid gap-3 md:grid-cols-2">
            {cards.map((card, index) => (
              <QuestionCard key={`${card.key}-${order}`} card={card} index={index} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
};

export default StudyPage;
