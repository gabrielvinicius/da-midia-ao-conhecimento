import { FileText, HardDrive, Languages, Shield } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { cn } from "@/lib/utils";
import { getStatusToken } from "../lib/status-helpers";
import type { PipelineStep } from "../lib/pipelineSteps";

type Props = {
  filename: string;
  fileSize: string;
  storage: string;
  language: string;
  steps: PipelineStep[];
};

/** Dados técnicos da mídia e o estado de cada etapa do processamento. */
export function MediaSystemCard({ filename, fileSize, storage, language, steps }: Props) {
  return (
    <Card className="border border-slate-200 bg-white shadow-sm">
      <CardHeader className="pb-3 border-b border-slate-50">
        <CardTitle className="text-xs font-bold uppercase tracking-widest text-slate-400">Dados do Sistema</CardTitle>
      </CardHeader>
      <CardContent className="pt-4 space-y-4 text-sm">
        <div className="flex justify-between py-1.5">
          <span className="text-muted-foreground flex items-center gap-2"><FileText className="h-3.5 w-3.5"/> Nome</span>
          <span className="font-medium truncate max-w-[150px] text-slate-700" title={filename}>{filename}</span>
        </div>
        <div className="flex justify-between py-1.5">
          <span className="text-muted-foreground flex items-center gap-2"><Shield className="h-3.5 w-3.5"/> Tamanho</span>
          <span className="font-medium text-slate-700">{fileSize}</span>
        </div>
        <div className="flex justify-between py-1.5">
          <span className="text-muted-foreground flex items-center gap-2"><HardDrive className="h-3.5 w-3.5"/> Storage</span>
          <span className="font-medium text-slate-700">{storage}</span>
        </div>
        <div className="flex justify-between py-1.5">
          <span className="text-muted-foreground flex items-center gap-2"><Languages className="h-3.5 w-3.5"/> Idioma</span>
          <span className="font-medium text-slate-700">{language}</span>
        </div>
        
        <div className="pt-4 border-t border-slate-50">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-4">Etapas de Processamento</p>
          <div className="space-y-3">
            {steps.map((step) => {
              const token = getStatusToken(step.status);
              return (
                <div key={step.key} className="group flex items-start justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <div className="mt-0.5">{token.icon}</div>
                    <div className="flex flex-col">
                      <span className="text-xs font-medium text-slate-700 leading-none">{step.label}</span>
                    </div>
                  </div>
                  <Badge className={cn("text-[9px] font-bold px-1.5 h-4 min-w-[70px] justify-center uppercase tracking-tighter", token.badge)}>
                    {token.label}
                  </Badge>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
