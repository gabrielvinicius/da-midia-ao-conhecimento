import { ReactNode } from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import NumberTicker from "@/components/ui/NumberTicker";
import { cn } from "@/lib/utils";

const numberFormatter = new Intl.NumberFormat("pt-BR");

export const percentFormatter = (value?: number, decimals: number = 1) =>
  `${Number(value ?? 0).toFixed(decimals)}%`;

export const Sparkline = ({
  points,
  accentClass = "text-emerald-500",
}: {
  points?: number[];
  accentClass?: string;
}) => {
  if (!points?.length) {
    return <p className="text-xs text-muted-foreground">Sem dados suficientes.</p>;
  }

  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;

  const path = points
    .map((value, index) => {
      const x = points.length === 1 ? 0 : (index / (points.length - 1)) * 100;
      const normalized = 100 - ((value - min) / range) * 100;
      return `${index === 0 ? "M" : "L"}${x},${normalized}`;
    })
    .join(" ");

  const lastValue = points[points.length - 1];
  const lastY = 100 - ((lastValue - min) / range) * 100;

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-16 w-full">
      <path
        d={path}
        stroke="currentColor"
        strokeWidth={3}
        fill="none"
        className={cn(accentClass, "stroke-current")}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="100" cy={lastY} r={2.5} fill="currentColor" className={accentClass} />
    </svg>
  );
};

export const KpiCard = ({
  title,
  description,
  value,
  suffix = "",
  prefix = "",
  decimals = 0,
  icon,
  trendValue,
  trendLabel,
  isLoading,
  accent,
}: {
  title: string;
  description: string;
  value: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
  icon: ReactNode;
  trendValue?: number;
  trendLabel?: string;
  isLoading?: boolean;
  accent?: string;
}) => {
  const isPositive = (trendValue ?? 0) >= 0;
  return (
    <Card className={cn("relative overflow-hidden border border-border/70 bg-gradient-to-br", accent)}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
          <p className="text-xs text-muted-foreground/80">{description}</p>
        </div>
        <div className="rounded-full border bg-background/70 p-2 text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading ? (
          <Skeleton className="h-10 w-3/4" />
        ) : (
          <div className="text-3xl font-semibold tracking-tight">
            <NumberTicker value={value} decimals={decimals} prefix={prefix} suffix={suffix} />
          </div>
        )}
        {typeof trendValue === "number" && !isLoading ? (
          <div
            className={cn(
              "flex items-center text-xs font-medium",
              isPositive ? "text-emerald-500" : "text-red-500"
            )}
          >
            {isPositive ? <ArrowUpRight className="mr-1 h-3 w-3" /> : <ArrowDownRight className="mr-1 h-3 w-3" />}
            <span>{trendLabel ?? `${trendValue.toFixed(1)}% vs período anterior`}</span>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
};

export const DistributionBarList = ({
  distribution,
}: {
  distribution?: { type: string; count: number; percentage: number; success_rate?: number }[];
}) => {
  if (!distribution?.length) {
    return <p className="text-sm text-muted-foreground">Nenhum registro disponível.</p>;
  }

  const total = distribution.reduce((acc, item) => acc + item.count, 0);

  return (
    <div className="space-y-3">
      {distribution.map((item) => {
        const percent = total ? (item.count / total) * 100 : 0;
        return (
          <div key={item.type}>
            <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
              <span className="capitalize">{item.type}</span>
              <span>
                {numberFormatter.format(item.count)} · {percent.toFixed(1)}%
              </span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-muted">
              <div className="h-2 rounded-full bg-primary" style={{ width: `${percent}%` }} />
            </div>
            {item.success_rate !== undefined && (
              <p className="mt-1 text-[11px] text-muted-foreground">
                Taxa de sucesso: {percentFormatter(item.success_rate, 1)}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
};

export const RecommendationList = ({ items }: { items?: string[] }) => {
  if (!items?.length) {
    return <p className="text-sm text-muted-foreground">Nenhuma recomendação ativa.</p>;
  }
  return (
    <ul className="space-y-2 text-sm">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-2">
          <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
};

export const SuccessPill = ({
  label,
  rate,
  completed,
  total,
}: {
  label: string;
  rate: number;
  completed: number;
  total: number;
}) => (
  <div className="rounded-2xl border border-border/70 bg-background/60 p-4">
    <div className="flex items-center justify-between text-xs text-muted-foreground">
      <span>{label}</span>
      <Badge variant="secondary">{percentFormatter(rate)}</Badge>
    </div>
    <p className="mt-2 text-lg font-semibold">
      {numberFormatter.format(completed)} / {numberFormatter.format(total)}
    </p>
    <p className="text-xs text-muted-foreground">Concluídas x total monitorado</p>
  </div>
);

export const TrendBadge = ({ direction, value }: { direction?: string; value?: number }) => {
  if (!direction) {
    return <Badge variant="secondary">Estável</Badge>;
  }

  const directionLower = direction.toLowerCase();
  const isPositive = directionLower === "improving" || (value ?? 0) >= 0;

  return (
    <Badge variant={isPositive ? "secondary" : "destructive"} className="gap-1">
      {isPositive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
      {isPositive ? "Em alta" : "Em queda"}
    </Badge>
  );
};

export const statusTone = (score: number) => {
  if (score >= 85)
    return { label: "Ótimo", tone: "text-emerald-500", badge: "bg-emerald-500/10 text-emerald-500" };
  if (score >= 70)
    return { label: "Estável", tone: "text-amber-500", badge: "bg-amber-500/10 text-amber-600" };
  return { label: "Atenção", tone: "text-red-500", badge: "bg-red-500/10 text-red-500" };
};
