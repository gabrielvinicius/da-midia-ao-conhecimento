import { saveAs } from 'file-saver';
import { useSummary } from "../hooks/useSummary";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Download, Info, Sparkles } from "lucide-react";
import { SummaryStatus } from "@/types";
import { cn } from "@/lib/utils";

const SUMMARY_PROVIDER_META: Record<string, { label: string; description: string }> = {
  heuristic_interpretive: {
    label: "Resumo Interpretativo",
    description: "TextRank + timeline para narrativas ricas (sem dependências).",
  },
  keyword_highlighter: {
    label: "Resumo por Palavras-chave",
    description: "Lista frases com maior densidade de termos importantes.",
  },
  huggingface: {
    label: "HuggingFace",
    description: "Modelos T5/BART via transformers (ideal para resumos neurais).",
  },
  huggingface_t5_base: {
    label: "HuggingFace T5 Base",
    description: "T5-base equilibrado para textos curtos.",
  },
  huggingface_bart_large: {
    label: "HuggingFace BART Large",
    description: "Modelo BART-Large CNN focado em inglês.",
  },
  huggingface_pegasus: {
    label: "HuggingFace Pegasus",
    description: "Pegasus Multi-News para conteúdos longos.",
  },
  openai: {
    label: "OpenAI GPT",
    description: "Resumo abstrativo com modelos GPT (exige chave de API).",
  },
};

interface SummaryPanelProps {
  mediaId: string;
}

export const SummaryPanel = ({ mediaId }: SummaryPanelProps) => {
  const { data: summary, isLoading, isError } = useSummary(mediaId);
  const providerInfo = summary?.provider ? SUMMARY_PROVIDER_META[summary.provider] : undefined;

  const handleDownload = () => {
    if (summary && summary.text) {
      const blob = new Blob([summary.text], { type: "text/plain;charset=utf-8" });
      saveAs(blob, `summary-${mediaId}.txt`);
    }
  };

  const canDownload = summary?.status === SummaryStatus.COMPLETED && !!summary.text;

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="space-y-2">
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-20 w-full" />
        </div>
      );
    }

    if (isError) {
      return <p className="text-destructive">Erro ao carregar resumo.</p>;
    }

    if (!summary) {
      return <p className="text-muted-foreground">O resumo ainda não foi iniciado.</p>;
    }

    switch (summary.status) {
      case SummaryStatus.PENDING:
      case SummaryStatus.PROCESSING:
        return (
          <div className="space-y-2 text-sm text-muted-foreground">
            <p className="font-medium text-slate-900">Gerando resumo inteligente...</p>
            <p>Nossa engine está identificando os principais tópicos antes de sintetizar.</p>
          </div>
        );
      case SummaryStatus.COMPLETED:
        return (
          <div className="space-y-4">
            {summary.text && (
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{summary.text}</p>
            )}
            {summary.bullet_points && summary.bullet_points.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-[0.3em]">Destaques</p>
                <ul className="list-disc space-y-1 pl-4 text-sm">
                  {summary.bullet_points.map((point, index) => (
                    <li key={`${point}-${index}`}>{point}</li>
                  ))}
                </ul>
              </div>
            )}
            {summary.key_topics && summary.key_topics.length > 0 && (
              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                {summary.key_topics.slice(0, 6).map((topic, index) => (
                  <Badge key={`${topic}-${index}`} variant="outline" className="rounded-full bg-slate-50">
                    {topic}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        );
      case SummaryStatus.FAILED:
        return (
          <p className="text-destructive">
            Falha no resumo: {summary.error_message || "Erro desconhecido"}
          </p>
        );
      default:
        return <p className="text-muted-foreground">Status de resumo desconhecido.</p>;
    }
  };

  return (
    <Card className="border border-[#ede4d5] bg-white text-slate-900">
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.4em] text-muted-foreground">Insights</p>
            <CardTitle className="text-2xl">Resumo inteligente</CardTitle>
            <CardDescription className="space-y-1">
              <span>Resumo interpretativo exclusivo.</span>
              {providerInfo?.description && (
                <span className="flex items-center gap-1 text-xs">
                  <Info className="h-3 w-3" /> {providerInfo.description}
                </span>
              )}
            </CardDescription>
          </div>
          <button
            onClick={handleDownload}
            disabled={!canDownload}
            className={cn(
              "inline-flex h-10 items-center rounded-full border border-[#f2eadf] bg-[#fefbf6] px-4 text-sm font-medium text-slate-900",
              canDownload ? "hover:bg-white" : "opacity-50 cursor-not-allowed"
            )}
          >
            <span className="mr-2 text-xs uppercase tracking-[0.3em]">Exportar</span>
            <Download className="h-4 w-4" />
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {summary?.provider && (
            <Badge variant="outline" className="rounded-full border border-[#f2eadf] bg-[#fdfbf6] text-slate-800">
              <Sparkles className="mr-1 h-3 w-3 text-amber-500" />
              {providerInfo?.label ?? summary.provider}
            </Badge>
          )}
          {summary?.strategy && (
            <Badge variant="secondary" className="rounded-full border border-[#f2eadf] bg-[#fdfbf6] text-slate-800">
              Estratégia: {summary.strategy}
            </Badge>
          )}
          {summary && (
            <Badge variant="secondary" className="rounded-full border border-[#f2eadf] bg-[#fdfbf6] text-slate-800">
              {summary.status}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-slate-900">
        {renderContent()}
      </CardContent>
    </Card>
  );
};
