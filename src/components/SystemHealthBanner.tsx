import React from 'react';
import { useSystemStatusQuery } from '@/hooks/useQueries';
import { AlertCircle, Zap, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

export const SystemHealthBanner = () => {
  const { data: status } = useSystemStatusQuery();

  if (!status || status.pressure === 'low') return null;

  const pressureConfig = {
    moderate: {
      label: "Carga Moderada",
      message: "Há processamentos em andamento; os próximos podem demorar um pouco mais.",
      icon: <Zap className="h-4 w-4" />,
      colors: "bg-blue-50 text-blue-700 border-blue-100"
    },
    high: {
      label: "Alta carga",
      message: "Memória da GPU ou processador quase no limite; novos processamentos esperam na fila.",
      icon: <Zap className="h-4 w-4 animate-pulse" />,
      colors: "bg-amber-50 text-amber-700 border-amber-100"
    },
    critical: {
      label: "Capacidade crítica",
      message: "Memória da GPU esgotada; o processamento atual pode falhar e ser repetido.",
      icon: <AlertCircle className="h-4 w-4" />,
      colors: "bg-red-50 text-red-700 border-red-100"
    }
  };

  const config = pressureConfig[status.pressure as keyof typeof pressureConfig];
  if (!config) return null;

  return (
    <div className={cn("px-4 py-2 border-b text-xs flex items-center justify-between transition-all animate-in slide-in-from-top duration-300", config.colors)}>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider">
          {config.icon}
          {config.label}
        </div>
        <span className="hidden md:inline opacity-80">{config.message}</span>
      </div>
      <div className="flex items-center gap-4 font-mono text-[10px]">
        {status.cpu_usage != null && <span>CPU: {status.cpu_usage.toFixed(0)}%</span>}
        {status.gpu_vram_usage != null && (
          <span>GPU: {(status.gpu_vram_usage * 100).toFixed(0)}%</span>
        )}
      </div>
    </div>
  );
};
