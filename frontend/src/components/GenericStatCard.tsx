import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import NumberTicker from "@/components/ui/NumberTicker";
import { cn } from "@/lib/utils";

interface GenericStatCardProps {
  title: string;
  value: number;
  description?: string;
  icon?: React.ReactNode;
  suffix?: string;
  decimals?: number;
  isLoading?: boolean;
  className?: string;
  valueClassName?: string;
}

export const GenericStatCard = ({
  title,
  value,
  description,
  icon,
  suffix = "",
  decimals = 0,
  isLoading = false,
  className,
  valueClassName,
}: GenericStatCardProps) => {
  return (
    <Card className={cn("border-[#ede4d5] bg-white shadow-sm hover:shadow-md transition-all duration-200", className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          {title}
        </CardTitle>
        {icon && <div className="p-2 rounded-full bg-slate-50 text-slate-900 border border-slate-100">{icon}</div>}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-9 w-24" />
        ) : (
          <div className={cn("text-3xl font-bold text-slate-900", valueClassName)}>
            <NumberTicker value={value} suffix={suffix} decimals={decimals} />
          </div>
        )}
        {description && (
          <p className="mt-1 text-xs text-muted-foreground leading-relaxed italic">
            {description}
          </p>
        )}
      </CardContent>
    </Card>
  );
};
