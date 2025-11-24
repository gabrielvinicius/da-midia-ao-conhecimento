import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Brain,
  Cpu,
  Gauge,
  Layers,
  LineChart,
  Radar,
  RefreshCcw,
  ShieldCheck,
  Timer,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";
import {
  useBusinessKpis,
  useMetricsSummary,
  useProcessingTrends,
  useSystemPerformance,
} from "../hooks/useAdminQueries";
import {
  DistributionBarList,
  KpiCard,
  RecommendationList,
  Sparkline,
  SuccessPill,
  TrendBadge,
  percentFormatter,
  statusTone,
} from "../components/AnalyticsWidgets";

const timeRangeOptions = [
  { label: "Última semana", value: "last_week" },
  { label: "Último mês", value: "last_month" },
  { label: "Último ano", value: "last_year" },
];

const numberFormatter = new Intl.NumberFormat("pt-BR");
const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

export const AdminAnalyticsPage = () => {
  const { user } = useAuth();
  const isAdmin = Boolean(user?.role && user.role.toString().toUpperCase().includes("ADMIN"));
  const [timeRange, setTimeRange] = useState<string>("last_week");

  const {
    data: performanceData,
    isLoading: isPerformanceLoading,
    isError: isPerformanceError,
  } = useSystemPerformance(timeRange, isAdmin);

  const {
    data: processingTrends,
    isLoading: isTrendsLoading,
    isError: isTrendsError,
  } = useProcessingTrends(30, isAdmin);

  const {
    data: metricsSummary,
    isLoading: isSummaryLoading,
    isError: isSummaryError,
  } = useMetricsSummary(isAdmin);

  const {
    data: businessKpis,
    isLoading: isKpisLoading,
    isError: isKpisError,
  } = useBusinessKpis(isAdmin);

  const throughput = metricsSummary?.performance_summary?.throughput_metrics;
  const resourceMetrics = metricsSummary?.performance_summary?.resource_metrics;
  const processingMetrics = metricsSummary?.performance_summary?.processing_metrics;
  const requestMetrics = metricsSummary?.performance_summary?.request_metrics;
  const successRates = metricsSummary?.success_rates;

  const distributionList = useMemo(() => {
    const distribution = metricsSummary?.media_distribution?.distribution;
    if (!distribution) return [];
    return Object.entries(distribution).map(([type, value]) => ({
      type,
      count: value.count ?? 0,
      percentage: value.percentage ?? 0,
      success_rate: value.success_rate,
    }));
  }, [metricsSummary]);

  const stagePills = useMemo(() => {
    const mapping: Record<string, string> = {
      media: "Pipeline completo",
      transcription: "Transcrição",
      summarization: "Sumarização",
    };
    return (Object.keys(mapping) as Array<keyof typeof mapping>).map((key) => ({
      label: mapping[key],
      rate: successRates?.[key]?.success_rate ?? 0,
      completed: successRates?.[key]?.completed ?? 0,
      total: successRates?.[key]?.total ?? 0,
    }));
  }, [successRates]);

  const sparklinePoints = useMemo(() => {
    if (!processingTrends?.current_week) return undefined;
    return [
      processingTrends.current_week.media?.success_rate ?? 0,
      processingTrends.current_week.transcription?.success_rate ?? 0,
      processingTrends.current_week.summarization?.success_rate ?? 0,
    ];
  }, [processingTrends]);

  if (!isAdmin) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Restrito a administradores</CardTitle>
          <CardDescription>Faça login com uma conta administrativa para visualizar as métricas globais.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const healthScore = performanceData?.overall_health_score ?? 0;
  const tone = statusTone(healthScore);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-muted-foreground">Painel de inteligência operacional</p>
          <h1 className="text-3xl font-semibold">Analytics & Observabilidade</h1>
          <p className="text-sm text-muted-foreground">Acompanhe o pulso da plataforma com KPIs, tendências e alertas automáticos.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 rounded-2xl border bg-muted/60 p-1">
          {timeRangeOptions.map((option) => (
            <Button
              key={option.value}
              size="sm"
              variant={option.value === timeRange ? "default" : "ghost"}
              onClick={() => setTimeRange(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      {(isPerformanceError || isTrendsError || isSummaryError || isKpisError) && (
        <Card className="border-red-500/40 bg-red-500/5">
          <CardHeader className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-semibold text-red-500">
              <AlertTriangle className="h-4 w-4" />
              <span>Nem todos os painéis puderam ser carregados.</span>
            </div>
            <CardDescription>
              Recarregue a página após garantir que o backend `/monitoring/*` está acessível e que seu usuário mantém a role ADMIN.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title="Uploads monitorados"
          description="Base dos últimos 30 dias"
          value={businessKpis?.total_uploads ?? 0}
          icon={<Layers className="h-4 w-4" />}
          trendValue={processingMetrics?.completed ? ((processingMetrics.completed / Math.max(processingMetrics.total_processing || 1, 1)) * 100) - 100 : undefined}
          trendLabel={processingMetrics?.completed ? `${numberFormatter.format(processingMetrics.completed)} concluídos nesta janela` : undefined}
          isLoading={isKpisLoading}
          accent="from-background via-background to-emerald-950/10"
        />
        <KpiCard
          title="Taxa de sucesso"
          description="Pipeline ponta a ponta"
          value={performanceData?.success_rates?.media?.success_rate ?? businessKpis?.upload_success_rate_percent ?? 0}
          suffix="%"
          decimals={1}
          icon={<ShieldCheck className="h-4 w-4" />}
          trendValue={performanceData?.success_rates?.media?.success_rate}
          trendLabel="Sucesso em mídia"
          isLoading={isPerformanceLoading}
          accent="from-background via-background to-sky-900/10"
        />
        <KpiCard
          title="Receita estimada"
          description="Projeção baseada em uploads bem-sucedidos"
          value={businessKpis?.total_revenue_usd ?? 0}
          prefix="US$ "
          decimals={2}
          icon={<BarChart3 className="h-4 w-4" />}
          trendValue={businessKpis?.average_revenue_per_upload}
          trendLabel={businessKpis?.average_revenue_per_upload ? `Ticket médio US$ ${businessKpis.average_revenue_per_upload.toFixed(2)}` : undefined}
          isLoading={isKpisLoading}
          accent="from-background via-background to-amber-900/10"
        />
        <KpiCard
          title="Throughput diário"
          description="Itens processados por dia"
          value={throughput?.media_por_dia ?? 0}
          suffix=" itens"
          decimals={2}
          icon={<Activity className="h-4 w-4" />}
          trendValue={throughput?.taxa_conclusao_percent}
          trendLabel={throughput?.taxa_conclusao_percent ? `${throughput.taxa_conclusao_percent.toFixed(1)}% de conclusão` : undefined}
          isLoading={isSummaryLoading}
          accent="from-background via-background to-purple-900/10"
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Saúde operacional</CardTitle>
              <CardDescription>Score consolidado considerando sucesso por etapa e atividade dos usuários.</CardDescription>
            </div>
            <Badge className={cn("text-sm", tone.badge)}>{tone.label}</Badge>
          </CardHeader>
          <CardContent className="grid gap-6 md:grid-cols-2">
            <div>
              {isPerformanceLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : (
                <div className="space-y-4">
                  <div className="text-5xl font-semibold text-foreground">
                    {healthScore.toFixed(1)}
                    <span className="text-base text-muted-foreground">/100</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    O score considera pesos diferentes para mídia, transcrição e sumarização. Quanto mais próximo de 100, menor o risco operacional.
                  </p>
                  <RecommendationList items={performanceData?.recommendations} />
                </div>
              )}
            </div>
            <div>
              {isSummaryLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : (
                <div className="space-y-3">
                  {stagePills.map((pill) => (
                    <SuccessPill
                      key={pill.label}
                      label={pill.label}
                      rate={pill.rate}
                      completed={pill.completed}
                      total={pill.total}
                    />
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tendências semanais</CardTitle>
            <CardDescription>Comparativo entre a semana atual e a média mensal.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isTrendsLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <TrendBadge direction={processingTrends?.trend_direction} value={processingTrends?.trend_percentage} />
                  <span className="text-sm text-muted-foreground">
                    Variação {processingTrends?.trend_percentage?.toFixed(1)}%
                  </span>
                </div>
                <Sparkline points={sparklinePoints} accentClass="text-indigo-500" />
                <div className="rounded-xl border border-border/60 bg-muted/40 p-3 text-xs text-muted-foreground">
                  <p className="font-medium text-foreground">Insights automáticos</p>
                  <ul className="mt-2 space-y-1">
                    {(processingTrends?.insights ?? ["Sem alertas críticos nesta janela"]).map((insight) => (
                      <li key={insight} className="flex items-start gap-1.5">
                        <Brain className="mt-0.5 h-3.5 w-3.5 text-sky-500" />
                        <span>{insight}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Distribuição por tipo de mídia</CardTitle>
            <CardDescription>Volume, participação e taxa de sucesso por tipo.</CardDescription>
          </CardHeader>
          <CardContent>
            {isSummaryLoading ? <Skeleton className="h-24 w-full" /> : <DistributionBarList distribution={distributionList} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recursos & throughput</CardTitle>
            <CardDescription>Monitoramento simplificado dos recursos provisionados.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            {isSummaryLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <>
                <div className="rounded-2xl border border-border/70 p-4">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>CPU</span>
                    <Cpu className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="mt-2 text-2xl font-semibold">{percentFormatter(resourceMetrics?.cpu_usage_percent)}</p>
                  <p className="text-xs text-muted-foreground">Uso médio registrado</p>
                </div>
                <div className="rounded-2xl border border-border/70 p-4">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Memória</span>
                    <Gauge className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="mt-2 text-2xl font-semibold">{percentFormatter(resourceMetrics?.memory_usage_percent)}</p>
                  <p className="text-xs text-muted-foreground">Consumo médio de RAM</p>
                </div>
                <div className="rounded-2xl border border-border/70 p-4">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Solicitações</span>
                    <Radar className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="mt-2 text-2xl font-semibold">{numberFormatter.format(requestMetrics?.total_requests ?? 0)}</p>
                  <p className="text-xs text-muted-foreground">Total monitorado</p>
                </div>
                <div className="rounded-2xl border border-border/70 p-4">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Erro médio</span>
                    <RefreshCcw className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="mt-2 text-2xl font-semibold">{percentFormatter(requestMetrics?.error_rate_percent)}</p>
                  <p className="text-xs text-muted-foreground">Baseado nas últimas requisições</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Eficiência por etapa</CardTitle>
            <CardDescription>Tempo médio de processamento vs. volume concluído.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {isSummaryLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <>
                <div className="rounded-2xl border border-border/80 bg-background/80 p-4">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <LineChart className="h-4 w-4 text-sky-500" />
                    <span>Transcrição</span>
                  </div>
                  <p className="mt-2 text-3xl font-semibold">
                    {processingMetrics?.avg_transcription_seconds?.toFixed(1)}s
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {numberFormatter.format(processingMetrics?.completed ?? 0)} execuções concluídas nesta janela.
                  </p>
                </div>
                <div className="rounded-2xl border border-border/80 bg-background/80 p-4">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Timer className="h-4 w-4 text-emerald-500" />
                    <span>Sumarização</span>
                  </div>
                  <p className="mt-2 text-3xl font-semibold">
                    {processingMetrics?.avg_summarization_seconds?.toFixed(1)}s
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {numberFormatter.format(processingMetrics?.total_processing ?? 0)} itens processados no período.
                  </p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>KPIs de negócio</CardTitle>
            <CardDescription>Indicadores consolidados da operação comercial.</CardDescription>
          </CardHeader>
          <CardContent>
            {isKpisLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>Uploads bem-sucedidos</span>
                  <span className="font-semibold text-foreground">
                    {numberFormatter.format(businessKpis?.successful_uploads ?? 0)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>Taxa de sucesso</span>
                  <span className="font-semibold text-emerald-500">
                    {percentFormatter(businessKpis?.upload_success_rate_percent)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>Receita média por upload</span>
                  <span className="font-semibold text-foreground">
                    {currencyFormatter.format(businessKpis?.average_revenue_per_upload ?? 0)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>Conclusões registradas</span>
                  <span className="font-semibold text-foreground">
                    {numberFormatter.format(businessKpis?.processing_completions ?? 0)}
                  </span>
                </div>
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3 text-xs text-muted-foreground">
                  <p className="font-medium text-emerald-600">Atualizado em</p>
                  <p>{businessKpis?.calculated_at ? new Date(businessKpis.calculated_at).toLocaleString("pt-BR") : "—"}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
};

export default AdminAnalyticsPage;
