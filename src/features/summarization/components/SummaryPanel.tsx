import { useState } from "react";
import { toast } from "react-toastify";
import { Edit3, History, Save, ThumbsDown, ThumbsUp, X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/Button";
import { Markdown } from "@/components/ui/Markdown";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";
import { MediaStatus, isInProgress, type TextAnalysisResponse } from "@/types";
import { splitSummary } from "@/features/media/lib/analysisContent";
import { correctSummary, submitAnalysisFeedback } from "../api";
import { GroundingNotice, type GroundingReport } from "./GroundingNotice";

// De onde veio o resumo (registrado pelo backend em diagnostics.summary_source).
export const summarySourceLabel = (source?: unknown): string | null => {
  switch (source) {
    case "llm":
      return "Gerado pelo modelo principal";
    case "reserve":
      return "Gerado pelo modelo reserva";
    // "fallback" é de análises antigas: os dois modelos falharam.
    case "fallback":
    case "simplified":
    case "error":
      return "Resumo simplificado: o modelo de linguagem não respondeu";
    default:
      return null;
  }
};

/** Gênero do conteúdo identificado pela análise (diagnostics.genre), que orienta o resumo. */
const GENRE_LABELS: Record<string, string> = {
  aula: "Aula",
  palestra: "Palestra",
  opiniao: "Opinião / ensaio",
  reuniao: "Reunião",
  entrevista: "Entrevista / podcast",
  tutorial: "Tutorial",
  documento: "Documento",
};

export const genreLabel = (genre?: unknown): string | null =>
  typeof genre === "string" ? GENRE_LABELS[genre] ?? null : null;

interface SummaryPanelProps {
  analysis: TextAnalysisResponse | null | undefined;
  isLoading?: boolean;
  isError?: boolean;
  mediaStatus?: MediaStatus;
  onSeek?: (time: number) => void;
  /** Só o dono ou um administrador corrige e avalia. */
  canEdit?: boolean;
  /** Omite o título "# ..." do resumo (a página já o mostra no cabeçalho). */
  hideTitle?: boolean;
}

const withoutTitle = (markdown: string) => markdown.replace(/^\s*#\s+[^\n]*\n?/, "");

/**
 * O resumo da mídia, sem o apêndice (os trechos por tema e o que aparecia na
 * tela têm abas próprias). Correção com pré-visualização; a versão da IA
 * fica guardada e pode ser comparada.
 */
export const SummaryPanel = ({
  analysis,
  isLoading,
  isError,
  mediaStatus,
  onSeek,
  canEdit = true,
  hideTitle = false,
}: SummaryPanelProps) => {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [showOriginal, setShowOriginal] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-7 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-4/5" />
      </div>
    );
  }
  if (isError) return <p className="text-sm text-destructive">Não foi possível carregar o resumo.</p>;
  if (!analysis) {
    if (mediaStatus === MediaStatus.FAILED) {
      return <p className="text-sm text-muted-foreground">O processamento falhou antes do resumo.</p>;
    }
    return (
      <p className="text-sm text-muted-foreground">
        {isInProgress(mediaStatus)
          ? "O resumo aparece aqui assim que a análise terminar."
          : "Resumo ainda não disponível."}
      </p>
    );
  }

  const { body, appendix } = splitSummary(analysis.summary);
  const original = analysis.diagnostics?.original_ai_summary as string | undefined;
  const originalBody = original ? splitSummary(original).body : null;
  const corrected = Boolean(originalBody && originalBody !== body);

  const startEditing = () => {
    setDraft(body);
    setIsEditing(true);
  };

  const save = async () => {
    if (!draft.trim()) return;
    setSaving(true);
    try {
      // O apêndice volta junto: a busca e a verificação de fidelidade o usam.
      await correctSummary(analysis.analysis_id, draft.trim() + appendix);
      await queryClient.invalidateQueries({ queryKey: ["text-analysis"] });
      toast.success("Resumo corrigido. A versão da IA continua guardada.");
      setIsEditing(false);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Falha ao salvar a correção."));
    } finally {
      setSaving(false);
    }
  };

  const sendFeedback = async (score: number) => {
    try {
      await submitAnalysisFeedback(analysis.analysis_id, score);
      setFeedbackGiven(score);
      toast.success("Obrigado pela avaliação!");
    } catch (err) {
      toast.error(apiErrorMessage(err, "Falha ao registrar a avaliação."));
    }
  };

  if (isEditing) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Edite em Markdown (# título, ## seção, - item, **negrito**). A versão da IA continua guardada.
        </p>
        <div className="grid gap-4 lg:grid-cols-2">
          <textarea
            aria-label="Texto do resumo"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="min-h-[60vh] w-full resize-y rounded-xl border border-slate-200 bg-white p-4 font-mono text-[13px] leading-6 outline-none focus:ring-2 focus:ring-primary/20"
          />
          <div className="max-h-[60vh] overflow-y-auto rounded-xl border border-dashed border-slate-200 p-4" aria-label="Pré-visualização">
            <Markdown text={draft} />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)} disabled={saving}>
            <X className="mr-1 h-4 w-4" /> Cancelar
          </Button>
          <Button size="sm" onClick={save} disabled={saving || !draft.trim()}>
            <Save className="mr-1 h-4 w-4" /> {saving ? "Salvando..." : "Salvar correção"}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {corrected && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-sky-50 px-3 py-2 text-sm text-sky-900">
          <span>{showOriginal ? "Mostrando a versão original da IA." : "Resumo corrigido por você."}</span>
          <button
            type="button"
            onClick={() => setShowOriginal((v) => !v)}
            className="inline-flex items-center gap-1 font-medium underline-offset-2 hover:underline"
          >
            <History className="h-3.5 w-3.5" /> {showOriginal ? "Ver versão corrigida" : "Ver versão da IA"}
          </button>
        </div>
      )}

      {body ? (
        <Markdown
          text={(hideTitle ? withoutTitle : (t: string) => t)(showOriginal && originalBody ? originalBody : body)}
        />
      ) : (
        <p className="text-sm text-muted-foreground">A análise terminou sem um resumo.</p>
      )}

      {!corrected && (
        <GroundingNotice
          report={analysis.diagnostics?.grounding as GroundingReport | undefined}
          truncated={analysis.diagnostics?.summary_truncated === true}
          onSeek={onSeek}
        />
      )}

      {canEdit && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span>Este resumo foi útil?</span>
            {[
              { score: 1, icon: ThumbsUp, label: "Útil", on: "bg-emerald-100 text-emerald-700" },
              { score: -1, icon: ThumbsDown, label: "Não foi útil", on: "bg-rose-100 text-rose-700" },
            ].map(({ score, icon: Icon, label, on }) => (
              <button
                key={score}
                type="button"
                aria-label={label}
                aria-pressed={feedbackGiven === score}
                onClick={() => sendFeedback(score)}
                className={cn("rounded-full p-1.5 transition-colors", feedbackGiven === score ? on : "hover:bg-slate-100")}
              >
                <Icon className="h-4 w-4" />
              </button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={startEditing} disabled={!body} className="gap-1.5">
            <Edit3 className="h-3.5 w-3.5" /> Corrigir resumo
          </Button>
        </div>
      )}
    </div>
  );
};
