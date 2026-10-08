import { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import NumberTicker from "@/components/ui/NumberTicker";
import { cn } from "@/lib/utils";

export const percentFormatter = (value?: number, decimals: number = 1) =>
  `${Number(value ?? 0).toFixed(decimals)}%`;

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
