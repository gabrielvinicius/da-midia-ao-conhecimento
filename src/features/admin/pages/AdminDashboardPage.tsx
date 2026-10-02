import { Users, FolderKanban, Loader2, Activity, ShieldAlert, CheckCircle2 } from "lucide-react";
import { GenericStatCard } from "@/components/GenericStatCard";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { useSystemStats, useSystemHealth, useMediaProcessingStats } from "../hooks/useAdminQueries";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";
import { percentFormatter } from "../components/AnalyticsWidgets";

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
        <GenericStatCard
          title="Usuários cadastrados"
          value={stats?.total_users ?? 0}
          icon={<Users className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Contas ativas na plataforma"
        />
        <GenericStatCard
          title="Usuários ativos"
          value={stats?.active_users ?? 0}
          icon={<Activity className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Sessões ativas nas últimas 24h"
        />
        <GenericStatCard
          title="Mídias registradas"
          value={stats?.total_media ?? 0}
          icon={<FolderKanban className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Itens catalogados no pipeline"
        />
        <GenericStatCard
          title="Processando agora"
          value={stats?.processing_media ?? 0}
          icon={<Loader2 className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Fila atual de jobs"
        />
        <GenericStatCard
          title="Falhas acumuladas"
          value={stats?.failed_media ?? 0}
          icon={<ShieldAlert className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
          description="Mídias que exigem reprocessamento"
        />
        <GenericStatCard
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
                  <span className="font-medium text-slate-900">{health.status === "healthy" ? "Tudo funcionando" : "Com alertas"}</span>
                  <span className="text-xs text-muted-foreground">Atualizado {new Date(health.timestamp).toLocaleString("pt-BR")}</span>
                </div>
                <div className="text-muted-foreground">
                  Usuários ativos: {health.active_users}/{health.total_users}
                </div>
                <div className="text-muted-foreground">
                  Na fila: {health.waiting_media} · Processando: {health.processing_media} · Falhas nas últimas {health.failure_window_hours} h: {health.failed_media}
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
