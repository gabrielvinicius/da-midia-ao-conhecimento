import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowRight, CheckCircle2, FolderKanban, ListOrdered, Users } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";
import { cn } from "@/lib/utils";
import { useProcessingQueue, useSystemHealth, useSystemStats } from "../hooks/useAdminQueries";
import { formatElapsed } from "@/lib/processingLabels";

const STAGE_LABEL: Record<string, string> = { uploaded: "Aguardando", processing: "Transcrevendo", analyzing: "Analisando" };

type KpiProps = { title: string; value?: number; detail: string; icon: ReactNode; to?: string; alert?: boolean; isLoading: boolean };

const Kpi = ({ title, value, detail, icon, to, alert, isLoading }: KpiProps) => {
  const body = (
    <Card className={cn("h-full border-[#ede4d5] p-4 transition-colors", to && "hover:border-slate-400", alert && "border-rose-200 bg-rose-50/50")}>
      <p className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        {icon}
        {title}
      </p>
      {isLoading ? (
        <Skeleton className="mt-2 h-8 w-12" />
      ) : (
        <p className={cn("mt-1 text-3xl font-semibold", alert && "text-rose-700")}>{value ?? 0}</p>
      )}
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </Card>
  );
  return to ? (
    <Link to={to} className="block">
      {body}
    </Link>
  ) : (
    body
  );
};

export const AdminDashboardPage = () => {
  const stats = useSystemStats();
  const health = useSystemHealth();
  const queue = useProcessingQueue();

  if (stats.isError && health.isError) {
    return (
      <ErrorState
        title="Não foi possível carregar a administração"
        message="Verifique a conexão com o servidor e tente novamente."
        onRetry={() => {
          stats.refetch();
          health.refetch();
        }}
      />
    );
  }

  const s = stats.data;
  const h = health.data;
  const inQueue = (h?.waiting_media ?? 0) + (h?.processing_media ?? 0);
  const preview = queue.data?.items.slice(0, 5) ?? [];
  const stuck = queue.data?.items.filter((i) => i.stuck).length ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Resumo</h1>
        <p className="text-sm text-muted-foreground">O que acontece agora na plataforma e o que pede atenção.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <Kpi
          title="Usuários"
          value={s?.total_users}
          detail={`${s?.active_users ?? 0} contas ativas`}
          icon={<Users className="h-4 w-4" />}
          to="/admin/users"
          isLoading={stats.isLoading}
        />
        <Kpi
          title="Mídias"
          value={s?.total_media}
          detail={`${s?.completed_media ?? 0} concluídas (${Math.round(s?.success_rate ?? 0)}%)`}
          icon={<FolderKanban className="h-4 w-4" />}
          to="/admin/media"
          isLoading={stats.isLoading}
        />
        <Kpi
          title="Na fila agora"
          value={inQueue}
          detail={`${h?.waiting_media ?? 0} aguardando · ${h?.processing_media ?? 0} em processamento`}
          icon={<ListOrdered className="h-4 w-4" />}
          to="/admin/queue"
          alert={stuck > 0}
          isLoading={health.isLoading}
        />
        <Kpi
          title={`Falhas em ${h?.failure_window_hours ?? 24} h`}
          value={h?.failed_media}
          detail={`${s?.failed_media ?? 0} com falha no total`}
          icon={<AlertTriangle className="h-4 w-4" />}
          to="/admin/media"
          alert={(h?.failed_media ?? 0) > 0}
          isLoading={health.isLoading}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-[#ede4d5]">
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div>
              <CardTitle className="text-base">Fila de processamento</CardTitle>
              <CardDescription>As mídias em andamento mais antigas.</CardDescription>
            </div>
            <Link to="/admin/queue" className="flex items-center gap-1 whitespace-nowrap text-sm font-medium text-slate-900 hover:underline">
              Ver fila <ArrowRight className="h-4 w-4" />
            </Link>
          </CardHeader>
          <CardContent>
            {queue.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : preview.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma mídia na fila.</p>
            ) : (
              <ul className="divide-y divide-slate-100 text-sm">
                {preview.map((item) => (
                  <li key={item.media_id} className="flex items-center justify-between gap-3 py-2">
                    <span className="min-w-0 truncate" title={item.filename ?? undefined}>
                      {item.position}. {item.filename || item.media_id}
                    </span>
                    <span className={cn("whitespace-nowrap text-xs", item.stuck ? "font-medium text-amber-700" : "text-muted-foreground")}>
                      {STAGE_LABEL[item.status]} há {formatElapsed(item.stage_seconds)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="border-[#ede4d5]">
          <CardHeader>
            <CardTitle className="text-base">Alertas</CardTitle>
            <CardDescription>
              {h ? `Verificado ${new Date(h.timestamp).toLocaleTimeString("pt-BR")}` : "Situação do sistema"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {health.isLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : h?.issues?.length || stuck ? (
              <ul className="space-y-2 text-sm text-amber-800">
                {stuck > 0 && (
                  <li className="flex gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>
                      {stuck === 1 ? "1 mídia parece parada" : `${stuck} mídias parecem paradas`} na fila.{" "}
                      <Link to="/admin/queue" className="underline">
                        Ver fila
                      </Link>
                    </span>
                  </li>
                )}
                {h?.issues?.map((issue) => (
                  <li key={issue} className="flex gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{issue}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="flex items-center gap-2 text-sm text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
                Nenhum alerta no momento.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
