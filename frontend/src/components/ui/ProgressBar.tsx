import { cn } from "@/lib/utils";

interface ProgressBarProps {
  label: string;
  value: number;
  color?: string;
  className?: string;
  showPercent?: boolean;
}

export const ProgressBar = ({
  label,
  value,
  color = "bg-primary",
  className,
  showPercent = true,
}: ProgressBarProps) => {
  const safeValue = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;

  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        {showPercent && <span className="font-medium">{Math.round(safeValue)}%</span>}
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className={cn("h-full transition-all duration-500 ease-in-out", color)}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  );
};
