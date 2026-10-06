import React from 'react';
import { Badge } from "@/components/ui/Badge";
import { MediaStatus } from "@/types";
import { Clock, Loader2, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface MediaStatusBadgeProps {
  status: MediaStatus;
  className?: string;
  showIcon?: boolean;
}

const statusConfig: Record<MediaStatus, { label: string; color: string; bgColor: string; icon: React.ReactNode }> = {
  [MediaStatus.UPLOADED]: {
    label: "Enviado",
    color: "text-slate-600",
    bgColor: "bg-slate-100 border-slate-200",
    icon: <Clock className="h-3 w-3" />
  },
  [MediaStatus.PENDING]: {
    label: "Pendente",
    color: "text-yellow-600",
    bgColor: "bg-yellow-100 border-yellow-200",
    icon: <Clock className="h-3 w-3" />
  },
  [MediaStatus.PROCESSING]: {
    label: "Processando",
    color: "text-blue-600",
    bgColor: "bg-blue-100 border-blue-200",
    icon: <Loader2 className="h-3 w-3 animate-spin" />
  },
  [MediaStatus.ANALYZING]: {
    label: "Analisando",
    color: "text-violet-600",
    bgColor: "bg-violet-100 border-violet-200",
    icon: <Loader2 className="h-3 w-3 animate-spin" />
  },
  [MediaStatus.COMPLETED]: {
    label: "Concluído",
    color: "text-emerald-600",
    bgColor: "bg-emerald-100 border-emerald-200",
    icon: <CheckCircle className="h-3 w-3" />
  },
  [MediaStatus.FAILED]: {
    label: "Falhou",
    color: "text-red-600",
    bgColor: "bg-red-100 border-red-200",
    icon: <XCircle className="h-3 w-3" />
  }
};

export const MediaStatusBadge = ({ status, className, showIcon = true }: MediaStatusBadgeProps) => {
  const config = statusConfig[status] || statusConfig[MediaStatus.PENDING];

  return (
    <Badge 
      variant="outline" 
      className={cn(
        "gap-1 font-medium capitalize h-6 px-2 whitespace-nowrap", 
        config.bgColor, 
        config.color, 
        className
      )}
    >
      {showIcon && config.icon}
      {config.label}
    </Badge>
  );
};
