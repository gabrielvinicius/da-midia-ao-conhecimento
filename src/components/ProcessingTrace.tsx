import React, { useMemo } from 'react';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Info, Cpu, Zap, Box, ShieldCheck, Activity, Search, Sparkles } from "lucide-react";
import { Media, TextAnalysisResponse, MediaStatus } from "@/types";
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/contexts/WebSocketContext";

interface ProcessingTraceProps {
  media: Media;
  analysis?: TextAnalysisResponse | null;
}

export const ProcessingTrace = ({ media, analysis }: ProcessingTraceProps) => {
  const { notifications } = useWebSocket();
  
  // Real-time event tracking for this specific media
  const relevantEvents = useMemo(() => {
    return notifications
      .filter(n => n.variables?.media_id === media.id)
      .map(n => n.variables?.kind || 'unknown');
  }, [notifications, media.id]);

  const hasEvent = (kind: string) => relevantEvents.includes(kind);

  const hardware = analysis?.diagnostics?.hardware_target || "cpu";
  const engine = analysis?.diagnostics?.engine || "Adaptive Knowledge Pipeline";
  const computeType = analysis?.diagnostics?.compute_type || "optimized";

  const steps = [
    { 
      label: "Ingestão & Armazenamento", 
      desc: "Arquivo recebido e replicado.", 
      status: "success", 
      icon: <Box className="h-4 w-4" />,
      detail: `Provider: ${media.storage_provider || 'Local'}`
    },
    { 
      label: "Processamento Multimodal", 
      desc: "Extração de frames e áudio neural.", 
      status: media.status === MediaStatus.COMPLETED || media.status === MediaStatus.PROCESSING || hasEvent('transcription') ? "success" : "pending", 
      icon: <Activity className="h-4 w-4" />,
      detail: `Tipo: ${media.media_type}`
    },
    { 
      label: "Descoberta de Tópicos", 
      desc: "Mapeamento semântico via BERTopic.", 
      status: analysis || hasEvent('topic_modeling') ? "success" : "pending", 
      icon: <Search className="h-4 w-4" />,
      detail: `Hardware: ${hardware.toUpperCase()}`
    },
    { 
      label: "Síntese Interpretativa", 
      desc: "Geração de artigo via Llama 3.", 
      status: analysis?.summary || hasEvent('summarization') ? "success" : "pending", 
      icon: <Sparkles className="h-4 w-4" />,
      detail: `Engine: ${engine}`
    }
  ];

  const currentStatus = useMemo(() => {
    if (media.status === MediaStatus.FAILED) return "FALHA NO SISTEMA";
    if (analysis?.summary) return "CONHECIMENTO CONSOLIDADO";
    if (hasEvent('summarization')) return "SINTETIZANDO ARTIGO...";
    if (hasEvent('topic_modeling')) return "MAPEANDO TÓPICOS...";
    if (media.status === MediaStatus.PROCESSING) return "PROCESSANDO MÍDIA...";
    return "AGUARDANDO INÍCIO";
  }, [media.status, analysis, relevantEvents]);

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-muted-foreground hover:text-primary transition-all">
          <Zap className={cn("h-3.5 w-3.5", media.status === MediaStatus.PROCESSING ? "text-amber-500 animate-pulse" : "text-muted-foreground")} />
          <span className="text-[10px] uppercase tracking-wider font-bold">Diagnóstico 8.0</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px] border-[#ede4d5] bg-[#fdfbf6] shadow-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Cpu className="h-5 w-5 text-purple-600" />
            Rastro de Inteligência
          </DialogTitle>
          <DialogDescription className="text-slate-600">
            Acompanhe a execução do pipeline de soberania de conhecimento em tempo real.
          </DialogDescription>
        </DialogHeader>
        
        <div className="mt-6 space-y-6">
          {steps.map((step, i) => (
            <div key={i} className="flex gap-4 relative group">
              {i < steps.length - 1 && (
                <div className={cn(
                  "absolute left-[17px] top-8 w-[2px] h-6 transition-colors duration-500",
                  step.status === 'success' ? "bg-emerald-200" : "bg-slate-100"
                )} />
              )}
              <div className={cn(
                "h-9 w-9 rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-500 shadow-sm",
                step.status === 'success' 
                  ? "bg-emerald-50 border-emerald-500 text-emerald-600 scale-110" 
                  : "bg-white border-slate-200 text-slate-300"
              )}>
                {step.icon}
              </div>
              <div className="space-y-1">
                <p className={cn(
                  "text-sm font-bold transition-colors", 
                  step.status === 'success' ? "text-slate-900" : "text-slate-400"
                )}>
                  {step.label}
                </p>
                <p className="text-[11px] text-muted-foreground leading-tight">{step.desc}</p>
                {step.status === 'success' && (
                  <div className="inline-block px-2 py-0.5 rounded-md bg-white border border-slate-100 text-[9px] font-mono text-slate-500 mt-1 shadow-sm">
                    {step.detail}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 p-4 rounded-2xl bg-slate-900 text-white shadow-inner">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">Live System Status</span>
            <div className="flex items-center gap-1.5">
              <span className={cn(
                "h-1.5 w-1.5 rounded-full animate-pulse",
                media.status === MediaStatus.FAILED ? "bg-red-500" : "bg-emerald-500"
              )} />
              <span className="text-[10px] font-mono text-emerald-400">ONLINE</span>
            </div>
          </div>
          <div className="space-y-1.5 font-mono text-[10px] leading-relaxed">
            <p><span className="text-slate-500">ID:</span> {media.id.slice(0, 18)}...</p>
            <p><span className="text-slate-500">HW:</span> {hardware.toUpperCase()} @ {computeType}</p>
            <p><span className="text-slate-500">OP:</span> <span className="text-amber-400">{currentStatus}</span></p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Internal minimal badge for clean look
const Badge = ({ children, className }: { children: React.ReactNode, className?: string }) => (
  <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold border", className)}>
    {children}
  </span>
);