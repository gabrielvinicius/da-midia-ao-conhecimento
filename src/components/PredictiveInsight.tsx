import React from 'react';
import { useAnalysisEstimationQuery } from '@/hooks/useQueries';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { BrainCircuit, Clock, Gauge, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PredictiveInsightProps {
  mediaId: string;
  isEnabled: boolean;
}

export const PredictiveInsight = ({ mediaId, isEnabled }: PredictiveInsightProps) => {
  const { data: est, isLoading } = useAnalysisEstimationQuery(mediaId, isEnabled);

  if (!isEnabled || isLoading || !est) return null;

  const riskColors = {
    safe: "text-emerald-500 bg-emerald-50 border-emerald-100",
    warning: "text-amber-500 bg-amber-50 border-amber-100",
    dangerous: "text-rose-500 bg-rose-50 border-rose-100",
    terminal: "text-red-700 bg-red-100 border-red-200",
  };

  return (
    <Card className="border-[#ede4d5] bg-[#fdfbf6] shadow-sm overflow-hidden animate-in fade-in slide-in-from-top-2 duration-500">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            <BrainCircuit className="h-4 w-4 text-purple-500" />
            Observabilidade Preditiva
          </div>
          <Badge className={cn("text-[10px] uppercase font-bold", riskColors[est.risk])}>
            Risco: {est.risk}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-white border border-slate-100 shadow-sm">
              <Clock className="h-4 w-4 text-sky-500" />
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground uppercase">Tempo Est.</p>
              <p className="text-sm font-bold text-slate-900">~{est.estimated_seconds.toFixed(0)}s</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-white border border-slate-100 shadow-sm">
              <Gauge className="h-4 w-4 text-amber-500" />
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground uppercase">VRAM Est.</p>
              <p className="text-sm font-bold text-slate-900">{est.vram_gb.toFixed(1)} GB</p>
            </div>
          </div>
        </div>

        {est.risk !== 'safe' && (
          <div className="mt-3 flex gap-2 p-2 rounded-lg bg-white/50 border border-slate-200/50 text-[11px] text-slate-600 leading-tight">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
            <span>{est.recommendation}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
