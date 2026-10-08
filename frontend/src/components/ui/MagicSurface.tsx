import { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { cn } from "@/lib/utils";

type MagicSurfaceProps = {
  title?: string;
  description?: string;
  className?: string;
  children: ReactNode;
};

export const MagicSurface = ({ title, description, className, children }: MagicSurfaceProps) => {
  return (
    <Card className={cn("border border-[#ede4d5] bg-white text-slate-900", className)}>
      {(title || description) && (
        <CardHeader className="space-y-1">
          {title && <CardTitle className="text-base font-semibold text-slate-900">{title}</CardTitle>}
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
      )}
      <CardContent className="space-y-2 text-slate-900">{children}</CardContent>
    </Card>
  );
};

export default MagicSurface;
