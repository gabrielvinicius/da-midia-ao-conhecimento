import { Monitor } from "lucide-react";

import type { TextAnalysisResponse } from "@/types";
import { TimeLink } from "@/features/summarization/components/StudyAids";
import { screenMomentsOf } from "../lib/analysisContent";

/** O que aparecia na tela nos quadros descritos do vídeo, com o momento de cada um. */
export const ScreenPanel = ({
  analysis,
  onSeek,
}: {
  analysis: TextAnalysisResponse | null | undefined;
  onSeek?: (time: number) => void;
}) => {
  const moments = screenMomentsOf(analysis);
  if (!moments.length) return <p className="text-sm text-muted-foreground">Nenhum quadro do vídeo foi descrito.</p>;
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Descrições automáticas de alguns quadros do vídeo, usadas como contexto do resumo.
      </p>
      <ol className="space-y-2">
        {moments.map((moment, index) => (
          <li key={index} className="flex gap-3 rounded-xl border border-slate-200 bg-white p-3">
            <Monitor className="mt-1 h-4 w-4 shrink-0 text-slate-400" />
            <div className="space-y-1">
              {moment.start != null && <TimeLink seconds={moment.start} onSeek={onSeek} />}
              <p className="text-sm leading-6 text-slate-700">{moment.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
};
