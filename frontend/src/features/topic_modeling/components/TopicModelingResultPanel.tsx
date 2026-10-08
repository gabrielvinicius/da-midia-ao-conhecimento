import { useState } from "react";
import { toast } from "react-toastify";
import { useQueryClient } from "@tanstack/react-query";
import { Check, Edit3, X } from "lucide-react";

import { Input } from "@/components/ui/Input";
import { apiErrorMessage } from "@/lib/errors";
import type { TextAnalysisResponse, TextAnalysisTopic } from "@/types";
import { topicsInOrder } from "@/features/media/lib/analysisContent";
import { renameTopic } from "@/features/summarization/api";
import { TimeLink } from "@/features/summarization/components/StudyAids";

/**
 * Temas da mídia, na ordem em que aparecem: título (corrigível), momento em
 * que começa, um trecho representativo e as palavras-chave.
 */
export const TopicModelingResultPanel = ({
  analysis,
  onSeek,
  canEdit = true,
}: {
  analysis: TextAnalysisResponse | null | undefined;
  onSeek?: (time: number) => void;
  canEdit?: boolean;
}) => {
  if (!analysis) return null;
  const topics = topicsInOrder(analysis);
  if (!topics.length) {
    // Etapas registradas sem a de temas: o fator foi desligado (ANALYSIS_FACTORS).
    const steps = analysis.diagnostics?.steps as Record<string, string> | undefined;
    return (
      <p className="text-sm text-muted-foreground">
        {steps && !("topic_modeling" in steps) ? "Os temas não foram analisados nesta mídia." : "Nenhum tópico detectado."}
      </p>
    );
  }
  const total = topics.reduce((sum, t) => sum + (t.size || 0), 0) || 1;

  return (
    <ol className="space-y-3">
      {topics.map((topic) => (
        <TopicItem
          key={topic.topic_id}
          topic={topic}
          share={(topic.size || 0) / total}
          analysisId={analysis.analysis_id}
          onSeek={onSeek}
          canEdit={canEdit}
        />
      ))}
    </ol>
  );
};

const TopicItem = ({
  topic,
  share,
  analysisId,
  onSeek,
  canEdit,
}: {
  topic: TextAnalysisTopic;
  share: number;
  analysisId: string;
  onSeek?: (time: number) => void;
  canEdit: boolean;
}) => {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(topic.title ?? "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!title.trim()) return;
    setSaving(true);
    try {
      await renameTopic(analysisId, topic.topic_id, title.trim());
      await queryClient.invalidateQueries({ queryKey: ["text-analysis"] });
      setEditing(false);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Não foi possível salvar o título do tema."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <li className="group rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-3">
        {topic.start != null && <span className="pt-0.5"><TimeLink seconds={topic.start} onSeek={onSeek} /></span>}
        {editing ? (
          <div className="flex flex-1 items-center gap-2">
            <Input
              aria-label="Título do tema"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") save();
                if (e.key === "Escape") setEditing(false);
              }}
              autoFocus
            />
            <button type="button" aria-label="Salvar título" onClick={save} disabled={saving} className="rounded-md p-1.5 text-emerald-700 hover:bg-emerald-50">
              <Check className="h-4 w-4" />
            </button>
            <button type="button" aria-label="Cancelar" onClick={() => setEditing(false)} className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100">
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <h3 className="flex-1 text-[15px] font-semibold leading-snug text-slate-900">
            {topic.title || "Tema"}
            {topic.original_title && (
              <span className="ml-2 align-middle text-[11px] font-normal text-sky-700" title={`Título da IA: ${topic.original_title}`}>
                corrigido
              </span>
            )}
          </h3>
        )}
        {canEdit && !editing && (
          <button
            type="button"
            aria-label={`Corrigir o título do tema ${topic.title ?? ""}`}
            onClick={() => setEditing(true)}
            className="rounded-md p-1 text-slate-400 opacity-0 hover:bg-slate-100 hover:text-slate-700 focus-visible:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100"
          >
            <Edit3 className="h-3.5 w-3.5" />
          </button>
        )}
        <span className="shrink-0 text-xs tabular-nums text-slate-400" title="Parcela do conteúdo">
          {Math.round(share * 100)}%
        </span>
      </div>
      {topic.representative_snippets?.[0] && (
        <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-600">“{topic.representative_snippets[0].trim()}”</p>
      )}
      {topic.keywords?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {topic.keywords.slice(0, 6).map((kw) => (
            <span key={kw} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {kw}
            </span>
          ))}
        </div>
      )}
    </li>
  );
};
