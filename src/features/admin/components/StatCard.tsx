import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import NumberTicker from "@/components/ui/NumberTicker";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  isLoading?: boolean;
  description?: string;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  accent?: string;
}

export const StatCard = ({
  title,
  value,
  icon,
  isLoading = false,
  description,
  prefix,
  suffix,
  decimals = 0,
  accent,
}: StatCardProps) => {
  return (
    <Card className={cn("border border-border/60", accent)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-1/2" />
        ) : (
          <div className="text-2xl font-semibold">
            <NumberTicker value={value} prefix={prefix} suffix={suffix} decimals={decimals} />
          </div>
        )}
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </CardContent>
    </Card>
  );
};
