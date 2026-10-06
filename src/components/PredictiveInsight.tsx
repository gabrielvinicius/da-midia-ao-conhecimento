import { useAnalysisEstimationQuery } from '@/features/media/hooks/useMediaQueries';
import { Card, CardContent } from '@/components/ui/Card';
import { Clock } from 'lucide-react';

interface PredictiveInsightProps {
  mediaId: string;
  isEnabled: boolean;
}

export const formatEstimate = (seconds: number): string => {
  if (seconds < 90) return 'menos de 2 minutos';
  const minutes = Math.round(seconds / 60);
  if (minutes < 90) return `cerca de ${minutes} minutos`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `cerca de ${hours} h${rest ? ` ${rest} min` : ''}`;
};

/**
 * Previsão de quanto o processamento leva, a partir da velocidade real desta
 * instalação. Só aparece quando há base para estimar: um número inventado
 * seria pior do que nenhum.
 */
export const PredictiveInsight = ({ mediaId, isEnabled }: PredictiveInsightProps) => {
  const { data: est } = useAnalysisEstimationQuery(mediaId, isEnabled);

  if (!isEnabled || !est?.estimated_seconds) return null;

  return (
    <Card className="border-[#ede4d5] bg-[#fdfbf6] shadow-sm">
      <CardContent className="flex items-start gap-3 p-4">
        <Clock className="mt-0.5 h-4 w-4 shrink-0 text-sky-500" />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-slate-900">
            Processamento estimado em {formatEstimate(est.estimated_seconds)}
          </p>
          <p className="text-xs text-muted-foreground">
            {est.includes_analysis ? 'Transcrição e análise' : 'Transcrição'}, pela velocidade dos processamentos
            anteriores nesta instalação.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};
