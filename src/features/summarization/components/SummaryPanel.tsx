import { useState } from 'react'; // Add useState
import { saveAs } from 'file-saver';
import { useTextAnalysisByMediaIdQuery } from "@/hooks/useQueries";
import api from '@/lib/api'; // Import api for feedback calls
import { toast } from 'react-toastify';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Download, Info, Sparkles, ThumbsUp, ThumbsDown, Edit3, Save, X } from "lucide-react";
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
  if (analysis.summary) {
    return analysis.summary;
  }
  const topics = analysis.topics || [];
  const summaries = topics
    .map((t) => (t.summary_md || t.summary || "").trim())
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

const renderSummaryText = (text: string) => {
  if (!text) return null;

  // Split into lines to apply styling
  const lines = text.split("\n");
  
  return (
    <div className="space-y-3 text-sm leading-relaxed text-slate-800 font-sans">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        
        if (!trimmed) return <div key={i} className="h-2" />;

        // Header 1
        if (trimmed.startsWith("# ")) {
          return <h3 key={i} className="text-xl font-bold text-slate-900 mt-6 mb-3 tracking-tight">{trimmed.replace(/^#\s+/, "")}</h3>;
        }
        // Header 2 or 3
        if (trimmed.startsWith("## ") || trimmed.startsWith("### ")) {
          return <h4 key={i} className="text-lg font-semibold text-slate-800 mt-4 mb-2">{trimmed.replace(/^#+\s+/, "")}</h4>;
        }
        
        // List items
        if (trimmed.match(/^[-*]\s/)) {
          return (
            <div key={i} className="flex gap-3 ml-1">
              <span className="text-amber-500 mt-2 h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" />
              <p className="flex-1">
                {renderInlineMarkdown(trimmed.replace(/^[-*]\s/, ""))}
              </p>
            </div>
          );
        }

        // Blockquotes (New Support)
        if (trimmed.startsWith("> ")) {
          return (
            <div key={i} className="my-4 border-l-4 border-amber-500 bg-amber-50 pl-4 py-3 pr-4 rounded-r-lg italic text-slate-700 shadow-sm">
              {renderInlineMarkdown(trimmed.replace(/^>\s*/, ""))}
            </div>
          );
        }

        // Standard Paragraph
        return (
          <p key={i} className="text-justify">
            {renderInlineMarkdown(trimmed)}
          </p>
        );
      })}
    </div>
  );
};

// Helper for inline bold/italic
const renderInlineMarkdown = (text: string) => {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, j) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={j} className="font-bold text-slate-950">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
};

// De onde veio o resumo (registrado pelo backend em diagnostics.summary_source).
export const summarySourceLabel = (source?: unknown): string | null => {
  switch (source) {
    case "llm":
      return "Gerado pelo modelo principal";
    case "fallback":
      return "Gerado pelo modelo reserva";
    case "simplified":
    case "error":
      return "Resumo simplificado: o modelo de linguagem não respondeu";
    default:
      return null;
  }
};

export const SummaryPanel = ({ mediaId, mediaStatus }: SummaryPanelProps) => {
  const { data: analysis, isLoading, isError, refetch } = useTextAnalysisByMediaIdQuery(mediaId);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [feedbackGiven, setFeedbackGiven] = useState<number | null>(null);

  const provider = analysis?.provider || undefined;
  const providerInfo = provider ? SUMMARY_PROVIDER_META[provider] : undefined;
  const summaryText = analysis ? buildSummaryText(analysis) : "";

  const handleFeedback = async (score: number) => {
    if (!analysis) return;
    try {
      await api.post(`/text-analysis/${analysis.analysis_id}/feedback?score=${score}`);
      setFeedbackGiven(score);
      toast.success("Obrigado pelo feedback!");
    } catch (err) {
      toast.error("Falha ao registrar feedback.");
    }
  };

  const handleSaveCorrection = async () => {
    if (!analysis) return;
    try {
      // O texto vai no corpo: resumos longos podem exceder o limite de tamanho da URL.
      await api.put(`/text-analysis/${analysis.analysis_id}/summary`, { summary: editedText });
      toast.success("Resumo atualizado!");
      setIsEditing(false);
      refetch();
    } catch (err) {
      toast.error("Falha ao salvar correção.");
    }
  };

  const startEditing = () => {
    setEditedText(summaryText);
    setIsEditing(true);
  };

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
        {isEditing ? (
          <div className="space-y-3">
            <textarea
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              className="w-full h-64 p-3 text-sm border rounded-xl focus:ring-2 focus:ring-primary/20 outline-none font-sans leading-relaxed"
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)}>
                <X className="mr-1 h-4 w-4" /> Cancelar
              </Button>
              <Button size="sm" onClick={handleSaveCorrection}>
                <Save className="mr-1 h-4 w-4" /> Salvar Alterações
              </Button>
            </div>
          </div>
        ) : (
          <>
            {summaryText ? (
              renderSummaryText(summaryText)
            ) : (
              <p className="text-sm text-muted-foreground">
                A análise foi gerada, mas ainda não há um resumo consolidado disponível.
              </p>
            )}
            
            {/* Level 7.0 Feedback Loop Toolbar */}
            {analysis && (
              <div className="mt-6 flex items-center justify-between py-3 border-t border-slate-100 animate-in fade-in duration-700">
                <div className="flex items-center gap-4">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-widest">Avalie este resumo</span>
                  <div className="flex gap-1">
                    <button 
                      onClick={() => handleFeedback(1)}
                      className={cn("p-1.5 rounded-full transition-colors", feedbackGiven === 1 ? "bg-emerald-100 text-emerald-600" : "hover:bg-slate-100 text-slate-400")}
                    >
                      <ThumbsUp className="h-4 w-4" />
                    </button>
                    <button 
                      onClick={() => handleFeedback(-1)}
                      className={cn("p-1.5 rounded-full transition-colors", feedbackGiven === -1 ? "bg-rose-100 text-rose-600" : "hover:bg-slate-100 text-slate-400")}
                    >
                      <ThumbsDown className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <Button variant="ghost" size="sm" onClick={startEditing} className="text-slate-500 hover:text-primary gap-1.5 h-8">
                  <Edit3 className="h-3.5 w-3.5" />
                  <span className="text-[10px] uppercase font-bold">Corrigir</span>
                </Button>
              </div>
            )}
          </>
        )}
        
        {keyTopics.length > 0 && !isEditing && (
          <div className="mt-6 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span className="w-full text-[10px] uppercase tracking-widest text-slate-400 mb-1">Assuntos Relacionados</span>
            {keyTopics.map((topic, index) => (
              <Badge key={`${topic}-${index}`} variant="outline" className="rounded-full bg-slate-50 border-slate-200 text-slate-600">
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
            <CardTitle className="text-2xl">Resumo</CardTitle>
            <CardDescription className="space-y-1">
              <span>Gerado a partir da transcrição e, em vídeos, do que aparece na tela.</span>
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
          {analysis && summarySourceLabel(analysis.diagnostics?.summary_source) && (
            <Badge variant="secondary" className="rounded-full border border-[#f2eadf] bg-[#fdfbf6] text-slate-800">
              {summarySourceLabel(analysis.diagnostics?.summary_source)}
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
