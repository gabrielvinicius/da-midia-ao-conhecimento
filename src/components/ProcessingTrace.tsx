import React from 'react';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Info, Cpu, Zap, Box, ShieldCheck, Activity } from "lucide-react";
import { Media, TextAnalysisResponse } from "@/types";
import { cn } from "@/lib/utils";

interface ProcessingTraceProps {
  media: Media;
  analysis?: TextAnalysisResponse | null;
}

export const ProcessingTrace = ({ media, analysis }: ProcessingTraceProps) => {
  const hardware = analysis?.diagnostics?.hardware_target || "cpu";
  const engine = analysis?.diagnostics?.engine || "Standard Pipeline";
  const computeType = analysis?.diagnostics?.compute_type || "default";

  const steps = [
    { 
      label: "Ingestão", 
      desc: "Arquivo validado e armazenado.", 
      status: "success", 
      icon: <Box className="h-4 w-4" />,
      detail: `Provider: ${media.storage_provider || 'Local'}`
    },
    { 
      label: "Processamento Base", 
      desc: "Extração de áudio e metadados.", 
      status: media.status === 'completed' || media.status === 'processing' ? "success" : "pending", 
      icon: <Activity className="h-4 w-4" />,
      detail: `Tipo: ${media.media_type}`
    },
    { 
      label: "Inteligência Artificial", 
      desc: "Transcrição e análise neural.", 
      status: analysis ? "success" : "pending", 
      icon: <Zap className="h-4 w-4" />,
      detail: `Hardware: ${hardware.toUpperCase()} (${computeType})`
    },
    { 
      label: "Consolidação", 
      desc: "Geração de resumos e tópicos.", 
      status: analysis?.summary ? "success" : "pending", 
      icon: <ShieldCheck className="h-4 w-4" />,
      detail: `Engine: ${engine}`
    }
  ];

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-muted-foreground hover:text-primary">
          <Info className="h-3.5 w-3.5" />
          <span className="text-[10px] uppercase tracking-wider font-bold">Rastro do Processo</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px] border-[#ede4d5] bg-[#fdfbf6]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-purple-500" />
            Diagnóstico de Processamento
          </DialogTitle>
          <DialogDescription>
            Transparência total sobre como sua mídia foi analisada pelo sistema Nível 6.0.
          </DialogDescription>
        </DialogHeader>
        
        <div className="mt-4 space-y-6">
          {steps.map((step, i) => (
            <div key={i} className="flex gap-4 relative">
              {i < steps.length - 1 && (
                <div className="absolute left-[17px] top-8 w-[2px] h-6 bg-slate-200" />
              )}
              <div className={cn(
                "h-9 w-9 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors",
                step.status === 'success' ? "bg-emerald-50 border-emerald-500 text-emerald-600" : "bg-slate-50 border-slate-200 text-slate-400"
              )}>
                {step.icon}
              </div>
              <div className="space-y-1">
                <p className={cn("text-sm font-bold", step.status === 'success' ? "text-slate-900" : "text-slate-400")}>
                  {step.label}
                </p>
                <p className="text-xs text-muted-foreground">{step.desc}</p>
                {step.status === 'success' && (
                  <Badge variant="outline" className="text-[10px] bg-white font-mono mt-1">
                    {step.detail}
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 p-3 rounded-xl bg-slate-900 text-white text-[11px] font-mono leading-relaxed">
          <p className="text-emerald-400 mb-1">// System Log Snapshot</p>
          <p>MEDIA_ID: {media.id}</p>
          <p>HARDWARE: {hardware.toUpperCase()}</p>
          <p>STRATEGY: ADAPTIVE_CHUNKING</p>
          <p>STATUS: {media.status.toUpperCase()}</p>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Internal Badge for the component
const Badge = ({ children, className, variant }: any) => (
  <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border", className)}>
    {children}
  </span>
);
