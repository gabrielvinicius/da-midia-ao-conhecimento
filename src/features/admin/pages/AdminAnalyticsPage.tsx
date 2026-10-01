import { useState } from "react";
import { CheckCircle2, Clock, Layers, XCircle } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { KpiCard } from "../components/AnalyticsWidgets";
import { useMediaProcessingStats, useProcessingTimes } from "../hooks/useAdminQueries";
import type { ProcessingTimeItem } from "../api";

const periodOptions: { label: string; value?: number }[] = [
  { label: "Últimos 7 dias", value: 7 },
  { label: "Últimos 30 dias", value: 30 },
  { label: "Todo o período", value: undefined },
];

const TASK_LABELS: Record<string, string> = {
  transcription: "Transcrição",
  text_analysis: "Análise completa",
  "analysis.chunking": "Divisão em trechos",
  "analysis.sentiment": "Sentimento",
  "analysis.topic_modeling": "Temas",
  "analysis.topic_titles": "Títulos dos temas",
  "analysis.knowledge_indexing": "Indexação semântica",
  "analysis.visual_insight": "Análise visual",
  "analysis.release_memory": "Liberação de memória da GPU",
  "analysis.synthesis": "Resumo final",
  "analysis.grounding_check": "Verificação de fidelidade",
};

export const taskLabel = (task: string) => TASK_LABELS[task] ?? task;

export const formatSeconds = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return "—";
  if (value < 60) return `${value.toFixed(1)} s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes} min ${seconds} s`;
};

const formatFactor = (value: number | null | undefined): string =>
  value === null || value === undefined ? "—" : `${value.toFixed(2)}×`;

const ProcessingTimesTable = ({ items }: { items: ProcessingTimeItem[] }) => {
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Nenhuma execução registrada no período. Os tempos aparecem aqui depois que mídias forem processadas.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-muted-foreground">
          <tr>
            <th className="py-2 pr-4">Tarefa</th>
            <th className="py-2 pr-4">Modelo</th>
            <th className="py-2 pr-4 text-right">Execuções</th>
            <th className="py-2 pr-4 text-right">Falhas</th>
            <th className="py-2 pr-4 text-right">Média</th>
            <th className="py-2 pr-4 text-right">Mediana</th>
            <th className="py-2 pr-4 text-right">Máximo</th>
            <th className="py-2 text-right" title="Tempo de processamento dividido pela duração da mídia">
              Tempo real
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.task_type}-${item.model_name ?? ""}`} className="border-t">
              <td className="py-2 pr-4 font-medium">{taskLabel(item.task_type)}</td>
              <td className="py-2 pr-4 text-muted-foreground">{item.model_name ?? "—"}</td>
              <td className="py-2 pr-4 text-right">{item.runs}</td>
              <td className="py-2 pr-4 text-right">{item.failures}</td>
              <td className="py-2 pr-4 text-right">{formatSeconds(item.avg_seconds)}</td>
              <td className="py-2 pr-4 text-right">{formatSeconds(item.median_seconds)}</td>
              <td className="py-2 pr-4 text-right">{formatSeconds(item.max_seconds)}</td>
              <td className="py-2 text-right">{formatFactor(item.realtime_factor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const AdminAnalyticsPage = () => {
  const { user } = useAuth();
  const isAdmin = Boolean(user?.role && user.role.toString().toUpperCase().includes("ADMIN"));
  const [days, setDays] = useState<number | undefined>(30);

  const media = useMediaProcessingStats(isAdmin);
  const times = useProcessingTimes(days, isAdmin);

  if (!isAdmin) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Restrito a administradores</CardTitle>
          <CardDescription>Faça login com uma conta administrativa para visualizar as métricas.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (media.isError && times.isError) {
    return (
      <ErrorState
        title="Não foi possível carregar as métricas"
        message="Verifique a conexão com o servidor e tente novamente."
        onRetry={() => {
          media.refetch();
          times.refetch();
        }}
      />
    );
  }

  const stats = media.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Análises de processamento</h1>
        <p className="text-muted-foreground">
          Situação das mídias e tempos medidos em cada etapa do processamento.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title="Mídias"
          description="Total enviado à plataforma"
          value={stats?.total_media ?? 0}
          icon={<Layers className="h-5 w-5" />}
          isLoading={media.isLoading}
        />
        <KpiCard
          title="Concluídas"
          description="Processadas com sucesso"
          value={stats?.success_rate ?? 0}
          suffix="%"
          decimals={1}
          icon={<CheckCircle2 className="h-5 w-5" />}
          isLoading={media.isLoading}
        />
        <KpiCard
          title="Com falha"
          description="Podem ser reprocessadas"
          value={stats?.failed ?? 0}
          icon={<XCircle className="h-5 w-5" />}
          isLoading={media.isLoading}
        />
        <KpiCard
          title="Em processamento"
          description="Na fila ou em execução"
          value={stats?.processing ?? 0}
          icon={<Clock className="h-5 w-5" />}
          isLoading={media.isLoading}
        />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Tempos de processamento</CardTitle>
            <CardDescription>
              Na coluna "Tempo real", 0,50× significa que a etapa levou metade da duração da gravação.
            </CardDescription>
          </div>
          <select
            aria-label="Período"
            className="rounded-md border px-2 py-1 text-sm"
            value={days ?? "all"}
            onChange={(e) => setDays(e.target.value === "all" ? undefined : Number(e.target.value))}
          >
            {periodOptions.map((option) => (
              <option key={option.label} value={option.value ?? "all"}>
                {option.label}
              </option>
            ))}
          </select>
        </CardHeader>
        <CardContent>
          {times.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : times.isError ? (
            <p className="text-sm text-red-600">Não foi possível carregar os tempos de processamento.</p>
          ) : (
            <ProcessingTimesTable items={times.data?.items ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
};
