import { Users, FolderKanban, Loader2, Activity, ShieldAlert, CheckCircle2 } from "lucide-react";
import { StatCard } from "../components/StatCard";
import { useSystemStats, useSystemHealth, useMediaProcessingStats } from "../hooks/useAdminQueries";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";

const ProgressBar = ({ value = 0, label, color = "bg-primary" }: { value?: number; label: string; color?: string }) => {
  const safeValue = Number.isFinite(value) ? Math.max(0, value) : 0;
  return (
  <div>
    <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
      <span>{label}</span>
      <span>{safeValue.toFixed(1)}%</span>
    </div>
    <div className="h-2 rounded-full bg-muted">
      <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(safeValue, 100)}%` }} />
    </div>
  </div>
  );
};

export const AdminDashboardPage = () => {
  const { data: stats, isLoading } = useSystemStats();
  const { data: health, isLoading: isHealthLoading } = useSystemHealth();
  const { data: mediaStats, isLoading: isMediaStatsLoading } = useMediaProcessingStats();

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight mb-6">Admin Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Total Users"
          value={stats?.total_users ?? 0}
          icon={<Users className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
        />
        <StatCard
          title="Active Users"
          value={stats?.active_users ?? 0}
          icon={<Activity className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
        />
        <StatCard
          title="Total Media Files"
          value={stats?.total_media ?? 0}
          icon={<FolderKanban className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
        />
        <StatCard
          title="Currently Processing"
          value={stats?.processing_media ?? 0}
          icon={<Loader2 className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
        />
        <StatCard
          title="Failed Media"
          value={stats?.failed_media ?? 0}
          icon={<ShieldAlert className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
        />
          <StatCard
            title="Success Rate"
            value={`${(stats?.success_rate ?? 0).toFixed(1)}%`}
            icon={<CheckCircle2 className="h-4 w-4 text-muted-foreground" />}
            isLoading={isLoading}
          />
      </div>

      <div className="grid gap-4 lg:grid-cols-2 mt-6">
        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
            <CardDescription>Status atual dos serviços críticos.</CardDescription>
          </CardHeader>
          <CardContent>
            {isHealthLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : health ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${health.status === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                  <span className="text-sm font-medium capitalize">{health.status}</span>
                  <span className="text-xs text-muted-foreground">Atualizado {new Date(health.timestamp).toLocaleString()}</span>
                </div>
                <div className="text-sm text-muted-foreground">
                  Usuários ativos: {health.active_users}/{health.total_users}
                </div>
                <div className="text-sm text-muted-foreground">
                  Processando: {health.processing_media} · Falhas: {health.failed_media}
                </div>
                {health.issues && health.issues.length > 0 ? (
                  <ul className="text-sm list-disc pl-4 text-yellow-600">
                    {health.issues.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">Nenhum alerta no momento.</p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Não foi possível carregar o status de saúde.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Media Processing Mix</CardTitle>
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
                <p className="text-xs text-muted-foreground">
                  Total monitorado: {mediaStats.total_media}
                </p>
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
