import { saveAs } from 'file-saver';
import { useSummary } from "../hooks/useSummary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Download } from "lucide-react";
import { SummaryStatus } from "@/types";

interface SummaryPanelProps {
  mediaId: string;
}

export const SummaryPanel = ({ mediaId }: SummaryPanelProps) => {
  const { data: summary, isLoading, isError } = useSummary(mediaId);

  const handleDownload = () => {
    if (summary && summary.text) {
      const blob = new Blob([summary.text], { type: "text/plain;charset=utf-8" });
      saveAs(blob, `summary-${mediaId}.txt`);
    }
  };

  const canDownload = summary?.status === SummaryStatus.COMPLETED && !!summary.text;

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="space-y-2">
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-20 w-full" />
        </div>
      );
    }

    if (isError) {
      return <p className="text-destructive">Error loading summary.</p>;
    }

    if (!summary) {
      return <p className="text-muted-foreground">O resumo ainda não foi iniciado.</p>;
    }

    switch (summary.status) {
      case SummaryStatus.PENDING:
      case SummaryStatus.PROCESSING:
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Skeleton className="h-4 w-4 rounded-full" />
            <span>Processando resumo...</span>
          </div>
        );
      case SummaryStatus.COMPLETED:
        return <p className="whitespace-pre-wrap">{summary.text}</p>;
      case SummaryStatus.FAILED:
        return (
          <p className="text-destructive">
            Falha no resumo: {summary.error_message || "Erro desconhecido"}
          </p>
        );
      default:
        return <p className="text-muted-foreground">Status de resumo desconhecido.</p>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>Resumo</span>
          <Button variant="outline" size="icon" onClick={handleDownload} disabled={!canDownload} title="Baixar Resumo">
            <Download className="h-4 w-4" />
            <span className="sr-only">Baixar Resumo</span>
          </Button>
        </CardTitle>
        {summary && <Badge variant="secondary" className="w-fit mt-2">{summary.status}</Badge>}
      </CardHeader>
      <CardContent>
        {renderContent()}
      </CardContent>
    </Card>
  );
};
