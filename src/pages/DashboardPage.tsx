import * as React from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import NumberTicker from "@/components/ui/NumberTicker";
import { MagicSurface } from "@/components/ui/MagicSurface";
import { MediaCard } from "../features/media/components/MediaCard";
import { useMediaList } from "../features/media/hooks/useMedia";
import { useAuth } from "../contexts/AuthContext";
import { UserRole } from "@/types";
import {
  Upload,
  BarChart3,
  FileText,
  Video,
  Music,
  RefreshCw,
  Sparkles,
  Clock3,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

const DashboardPage = () => {
  const { data: media, isLoading, isError, error, refetch } = useMediaList();
  const { user } = useAuth();
  const isAdmin = user?.role === UserRole.ADMIN || user?.role?.toString().toUpperCase().includes("ADMIN");

  // Calcular estatísticas
  const stats = React.useMemo(() => {
    if (!media) return { total: 0, videos: 0, audios: 0, texts: 0, processing: 0, completed: 0, failed: 0 };
    
    return {
      total: media.length,
      videos: media.filter(m => m.media_type === 'VIDEO').length,
      audios: media.filter(m => m.media_type === 'AUDIO').length,
      texts: media.filter(m => m.media_type === 'TEXT').length,
      processing: media.filter(m => m.status === 'PROCESSING').length,
      completed: media.filter(m => m.status === 'COMPLETED').length,
      failed: media.filter(m => m.status === 'FAILED').length,
    };
  }, [media]);

  const completionRate = stats.total ? (stats.completed / stats.total) * 100 : 0;
  const failureRate = stats.total ? (stats.failed / stats.total) * 100 : 0;
  const processingRate = stats.total ? (stats.processing / stats.total) * 100 : 0;
  const lastUpload = media?.[0];

  const breakdown = [
    { label: "Vídeo", value: stats.videos, icon: <Video className="h-4 w-4" />, color: "bg-violet-500" },
    { label: "Áudio", value: stats.audios, icon: <Music className="h-4 w-4" />, color: "bg-emerald-500" },
    { label: "Texto", value: stats.texts, icon: <FileText className="h-4 w-4" />, color: "bg-sky-500" },
  ];

  const StatCard = ({
    title,
    value,
    suffix = "",
    description,
    icon,
  }: {
    title: string;
    value: number;
    suffix?: string;
    description: string;
    icon: React.ReactNode;
  }) => (
    <MagicSurface title={title} description={description}>
      <div className="flex.items-center justify-between">
        <div className="text-3xl font-semibold text-slate-900">
          <NumberTicker value={value} suffix={suffix} />
        </div>
        <div className="rounded-full bg-slate-100 p-2 text-slate-900">{icon}</div>
      </div>
    </MagicSurface>
  );

  const ProgressItem = ({ label, value, color }: { label: string; value: number; color: string }) => (
    <div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>{value.toFixed(1)}%</span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-muted">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );

  const renderStatsCards = () => (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <StatCard
        title="Total monitorado"
        value={stats.total}
        description={stats.processing ? `${stats.processing} em processamento` : "Nenhum processamento ativo"}
        icon={<FileText className="h-4 w-4" />}
      />
      <StatCard
        title="Taxa de conclusão"
        value={completionRate}
        suffix="%"
        description="Resumo das últimas execuções"
        icon={<CheckCircle2 className="h-4 w-4" />}
      />
      <StatCard
        title="Uploads recentes"
        value={media?.slice(0, 10).length ?? 0}
        description="Últimos itens enviados"
        icon={<Upload className="h-4 w-4" />}
      />
      <StatCard
        title="Taxa de falhas"
        value={failureRate}
        suffix="%"
        description={failureRate > 0 ? "Verifique itens com erro" : "Sem falhas no período"}
        icon={<AlertTriangle className="h-4 w-4" />}
      />
    </div>
  );

  const renderContent = () => {
    if (isLoading) {
      return (
        <>
          {/* Stats skeleton */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
          {/* Media grid skeleton */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        </>
      );
    }

    if (isError) {
      return (
        <div className="text-center py-16">
          <div className="text-destructive mb-4">
            <p>Erro ao carregar arquivos: {error?.message}</p>
          </div>
          <Button onClick={() => refetch()} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Tentar Novamente
          </Button>
        </div>
      );
    }

    if (!media || media.length === 0) {
      return (
        <div className="text-center py-16">
          <MagicSurface title="Nenhum arquivo encontrado" description="Envie sua primeira mídia para liberar os insights." className="max-w-md mx-auto">
            <Upload className="h-12 w-12 mx-auto text-slate-500 mb-4" />
            <Button asChild className="w-full">
              <Link to="/upload">
                <Upload className="mr-2 h-4 w-4" />
                Fazer Upload
              </Link>
            </Button>
          </MagicSurface>
        </div>
      );
    }

    return (
      <>
        {renderStatsCards()}
        <div className="grid gap-6 lg:grid-cols-3">
          <MagicSurface title="Seus arquivos" description="Consulte e acompanhe o status de cada mídia." className="lg:col-span-2">
            <div className="mb-4 flex gap-2">
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Atualizar
              </Button>
              <Button asChild size="sm">
                <Link to="/upload">
                  <Upload className="mr-2 h-4 w-4" />
                  Novo Upload
                </Link>
              </Button>
            </div>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
              {media.map((item) => (
                <MediaCard key={item.id} media={item} />
              ))}
            </div>
          </MagicSurface>

          <div className="space-y-4">
            <MagicSurface title="Distribuição por tipo" description="Visão rápida da proporção de mídias enviadas.">
              <div className="space-y-4">
                {breakdown.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-border/70 p-3">
                    <div className="flex items-center justify-between text-sm font-medium">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <span className={`rounded-full p-2 text-slate-900 ${item.color}`}>
                          {item.icon}
                        </span>
                        {item.label}
                      </div>
                      <span>{item.value}</span>
                    </div>
                  </div>
                ))}
              </div>
            </MagicSurface>

            <MagicSurface title="Saúde do pipeline" description="Taxas de processamento em tempo quase real.">
              <div className="space-y-3">
                <ProgressItem label="Concluídos" value={completionRate} color="bg-emerald-500" />
                <ProgressItem label="Processando" value={processingRate} color="bg-sky-500" />
                <ProgressItem label="Falhas" value={failureRate} color="bg-rose-500" />
              </div>
            </MagicSurface>

            <MagicSurface title="Último upload" description="Acompanhe o item mais recente enviado.">
                {lastUpload ? (
                  <div className="space-y-2 text-sm">
                    <p className="font-semibold text-foreground">{lastUpload.original_filename ?? "Arquivo sem nome"}</p>
                    <p className="text-muted-foreground">
                      Status: <span className="font-medium text-foreground">{lastUpload.status}</span>
                    </p>
                    <p className="text-muted-foreground">
                      Enviado em {new Date(lastUpload.created_at ?? Date.now()).toLocaleString("pt-BR")}
                    </p>
                    <Button asChild variant="secondary" size="sm" className="mt-2 w-full">
                      <Link to={`/media/${lastUpload.id}`}>Abrir detalhes</Link>
                    </Button>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Faça um upload para desbloquear esta visão.</p>
                )}
            </MagicSurface>
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="space-y-6">
      <MagicSurface title="Painel pessoal" description="Centralize uploads, progresso e insights.">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Bem-vindo de volta, {user?.email}</h1>
            <p className="text-sm text-slate-600">Tudo o que você processou e ainda está em fila, reunido neste painel.</p>
          </div>
          <div className="flex flex-col gap-2 text-sm">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-300" />
              <span>{stats.completed} arquivos concluídos</span>
            </div>
            <div className="flex.items-center gap-2">
              <Clock3 className="h-4 w-4 text-sky-300" />
              <span>{stats.processing} em processamento agora</span>
            </div>
            {isAdmin && (
              <Button asChild size="sm" variant="secondary" className="mt-2">
                <Link to="/admin/analytics">
                  <BarChart3 className="mr-2 h-4 w-4" />
                  Visão administrativa
                </Link>
              </Button>
            )}
          </div>
        </div>
      </MagicSurface>
      {renderContent()}
    </div>
  );
};

export default DashboardPage;
