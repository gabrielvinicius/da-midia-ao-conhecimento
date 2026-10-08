import { ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./Button";

type ErrorStateProps = {
  title?: string;
  message?: string;
  onRetry?: () => void;
  actionLabel?: string;
  icon?: ReactNode;
};

export const ErrorState = ({
  title = "Algo deu errado",
  message = "Não foi possível carregar os dados.",
  onRetry,
  actionLabel = "Tentar novamente",
  icon,
}: ErrorStateProps) => {
  return (
    <div className="text-center py-12 space-y-4">
      <div className="flex flex-col items-center gap-2 text-destructive">
        {icon ?? <AlertTriangle className="h-8 w-8" />}
        <p className="text-lg font-semibold">{title}</p>
      </div>
      <p className="text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="inline-flex items-center gap-2">
          <RefreshCw className="h-4 w-4" />
          {actionLabel}
        </Button>
      )}
    </div>
  );
};

export default ErrorState;
