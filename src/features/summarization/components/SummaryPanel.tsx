import { saveAs } from 'file-saver';
import { useTextAnalysisByMediaIdQuery } from "@/hooks/useQueries";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Download, Info, Sparkles } from "lucide-react";
import { MediaStatus, TextAnalysisResponse } from "@/types";
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
  mediaStatus?: MediaStatus;
}

const buildSummaryText = (analysis: TextAnalysisResponse): string => {
  const topics = analysis.topics || [];
  const summaries = topics
    .map((t) => (t.summary_md || "").trim())
    .filter(Boolean);
  if (summaries.length > 0) {
    return summaries.join("\n\n");
  }
  // Fallback: usar snippets representativos quando não há summary_md
  const snippets = topics
    .flatMap((t) => t.representative_snippets || [])
    .map((s) => String(s || "").trim())
    .filter(Boolean)
    .slice(0, 20);
  return snippets.join("\n");
};

export const SummaryPanel = ({ mediaId, mediaStatus }: SummaryPanelProps) => {
  const { data: analysis, isLoading, isError } = useTextAnalysisByMediaIdQuery(mediaId);
  const provider = analysis?.provider || undefined;
  const providerInfo = provider ? SUMMARY_PROVIDER_META[provider] : undefined;
  const summaryText = analysis ? buildSummaryText(analysis) : "";

  const handleDownload = () => {
    if (analysis && summaryText) {
      const blob = new Blob([summaryText], { type: "text/plain;charset=utf-8" });
      saveAs(blob, `summary-${mediaId}.txt`);
    }
  };

  const canDownload = Boolean(analysis && summaryText);

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

    if (!analysis) {
      if (mediaStatus === MediaStatus.FAILED) {
        return <p className="text-destructive">Falha no processamento da mídia.</p>;
      }
      if (mediaStatus === MediaStatus.PROCESSING) {
        return (
          <div className="space-y-2 text-sm text-muted-foreground">
            <p className="font-medium text-slate-900">Gerando resumo inteligente...</p>
            <p>Assim que a transcrição/extração finalizar, a análise será produzida.</p>
          </div>
        );
      }
      return <p className="text-muted-foreground">Resumo ainda não disponível.</p>;
    }

    const keyTopics = (analysis.topics || [])
      .flatMap((t) => t.keywords || [])
      .filter(Boolean)
      .slice(0, 10);

    return (
      <div className="space-y-4">
        {summaryText ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{summaryText}</p>
        ) : (
          <p className="text-sm text-muted-foreground">
            A análise foi gerada, mas ainda não há um resumo consolidado disponível.
          </p>
        )}
        {keyTopics.length > 0 && (
          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            {keyTopics.map((topic, index) => (
              <Badge key={`${topic}-${index}`} variant="outline" className="rounded-full bg-slate-50">
                {topic}
              </Badge>
            ))}
          </div>
        )}
      </div>
    );
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
          {provider && (
            <Badge variant="outline" className="rounded-full border border-[#f2eadf] bg-[#fdfbf6] text-slate-800">
              <Sparkles className="mr-1 h-3 w-3 text-amber-500" />
              {providerInfo?.label ?? provider}
            </Badge>
          )}
          {analysis && (
            <Badge variant="secondary" className="rounded-full border border-[#f2eadf] bg-[#fdfbf6] text-slate-800">
              {MediaStatus.COMPLETED}
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
