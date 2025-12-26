import { Users, FolderKanban, Loader2, Activity, ShieldAlert, CheckCircle2 } from "lucide-react";
import { StatCard } from "../components/StatCard";
import { useSystemStats, useSystemHealth, useMediaProcessingStats } from "../hooks/useAdminQueries";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";
import { percentFormatter } from "../components/AnalyticsWidgets";

const ProgressBar = ({ value = 0, label, color = "bg-primary" }: { value?: number; label: string; color?: string }) => {
  const safeValue = Number.isFinite(value) ? Math.max(0, value) : 0;
  return (
  <div>
    <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
      <span>{label}</span>
      <span>{percentFormatter(safeValue)}</span>
    </div>
    <div className="h-2 rounded-full bg-muted">
      <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(safeValue, 100)}%` }} />
    </div>
  </div>
  );
};

export const AdminDashboardPage = () => {
  const { data: stats, isLoading, isError: isStatsError, refetch: refetchStats } = useSystemStats();
  const { data: health, isLoading: isHealthLoading, isError: isHealthError, refetch: refetchHealth } = useSystemHealth();
  const { data: mediaStats, isLoading: isMediaStatsLoading, isError: isMediaStatsError, refetch: refetchMediaStats } = useMediaProcessingStats();

  if (isStatsError || isHealthError || isMediaStatsError) {
    return (
      <ErrorState
        title="Não foi possível carregar o painel admin"
        message="Verifique sua permissão ADMIN e a saúde do backend."
        onRetry={() => {
          refetchStats();
          refetchHealth();
          refetchMediaStats();
        }}
      />
    );
  }

  return (
    <div>
      <div className="mb-6">
        <p className="text-sm uppercase text-muted-foreground">Painel administrativo</p>
        <h1 className="text-3xl font-bold tracking-tight">Visão geral das operações</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Usuários cadastrados"
          value={stats?.total_users ?? 0}
          icon={<Users className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Contas ativas na plataforma"
        />
        <StatCard
          title="Usuários ativos"
          value={stats?.active_users ?? 0}
          icon={<Activity className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Sessões ativas nas últimas 24h"
        />
        <StatCard
          title="Mídias registradas"
          value={stats?.total_media ?? 0}
          icon={<FolderKanban className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Itens catalogados no pipeline"
        />
        <StatCard
          title="Processando agora"
          value={stats?.processing_media ?? 0}
          icon={<Loader2 className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Fila atual de jobs"
        />
        <StatCard
          title="Falhas acumuladas"
          value={stats?.failed_media ?? 0}
          icon={<ShieldAlert className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Mídias que exigem reprocessamento"
        />
        <StatCard
          title="Taxa de sucesso"
          value={stats?.success_rate ?? 0}
          suffix="%"
          decimals={1}
          icon={<CheckCircle2 className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Mídias concluídas na janela atual"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2 mt-6">
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Saúde do sistema</CardTitle>
            <CardDescription>Status consolidado dos serviços críticos.</CardDescription>
          </CardHeader>
          <CardContent>
            {isHealthLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : health ? (
              <div className="space-y-4 text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <span className={`h-2 w-2 rounded-full ${health.status === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                  <span className="font-medium capitalize text-slate-900">{health.status}</span>
                  <span className="text-xs text-muted-foreground">Atualizado {new Date(health.timestamp).toLocaleString("pt-BR")}</span>
                </div>
                <div className="text-muted-foreground">
                  Usuários ativos: {health.active_users}/{health.total_users}
                </div>
                <div className="text-muted-foreground">
                  Processando: {health.processing_media} · Falhas: {health.failed_media}
                </div>
                {health.issues && health.issues.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-4 text-amber-600">
                    {health.issues.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground">Nenhum alerta no momento.</p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Não foi possível carregar o status de saúde.</p>
            )}
          </CardContent>
        </Card>

        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Mix de processamento</CardTitle>
            <CardDescription>Distribuição das mídias por status.</CardDescription>
          </CardHeader>
          <CardContent>
            {isMediaStatsLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : mediaStats ? (
              <div className="space-y-4">
                <ProgressBar value={mediaStats.success_rate} label="Concluídos" color="bg-emerald-500" />
                <ProgressBar value={mediaStats.processing_rate} label="Processando" color="bg-blue-500" />
                <ProgressBar value={mediaStats.failure_rate} label="Falhas" color="bg-red-500" />
                <p className="text-xs text-muted-foreground">Total monitorado: {mediaStats.total_media}</p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Nenhuma estatística disponível.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
