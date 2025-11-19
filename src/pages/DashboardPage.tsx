import * as React from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import NumberTicker from "@/components/ui/NumberTicker";
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
    accent,
  }: {
    title: string;
    value: number;
    suffix?: string;
    description: string;
    icon: React.ReactNode;
    accent: string;
  }) => (
    <Card className={`border-none bg-gradient-to-br ${accent} text-white shadow-lg`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div>
          <CardTitle className="text-sm font-medium text-white/80">{title}</CardTitle>
          <p className="text-xs text-white/60">{description}</p>
        </div>
        <div className="rounded-full bg-white/15 p-2 text-white">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-semibold">
          <NumberTicker value={value} suffix={suffix} />
        </div>
      </CardContent>
    </Card>
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
        accent="from-slate-900 via-slate-800 to-slate-900"
      />
      <StatCard
        title="Taxa de conclusão"
        value={completionRate}
        suffix="%"
        description="Resumo das últimas execuções"
        icon={<CheckCircle2 className="h-4 w-4" />}
        accent="from-emerald-700 via-emerald-600 to-emerald-800"
      />
      <StatCard
        title="Uploads recentes"
        value={media?.slice(0, 10).length ?? 0}
        description="Últimos itens enviados"
        icon={<Upload className="h-4 w-4" />}
        accent="from-indigo-700 via-indigo-600 to-indigo-800"
      />
      <StatCard
        title="Taxa de falhas"
        value={failureRate}
        suffix="%"
        description={failureRate > 0 ? "Verifique itens com erro" : "Sem falhas no período"}
        icon={<AlertTriangle className="h-4 w-4" />}
        accent="from-rose-700 via-rose-600 to-rose-800"
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
          <Card className="max-w-md mx-auto">
            <CardHeader>
              <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <CardTitle>Nenhum arquivo encontrado</CardTitle>
              <CardDescription>
                Comece fazendo upload do seu primeiro arquivo de mídia para processar transcrições, resumos e análises.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link to="/upload">
                  <Upload className="mr-2 h-4 w-4" />
                  Fazer Upload
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return (
      <>
        {renderStatsCards()}
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-lg">Seus arquivos</CardTitle>
                <CardDescription>Consulte, atualize e acompanhe o status de cada mídia processada.</CardDescription>
              </div>
              <div className="flex gap-2">
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
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
                {media.map((item) => (
                  <MediaCard key={item.id} media={item} />
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Distribuição por tipo</CardTitle>
                <CardDescription>Visão rápida da proporção de mídias enviadas.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {breakdown.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-border/70 p-3">
                    <div className="flex items-center justify-between text-sm font-medium">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <span className={`rounded-full p-2 text-white ${item.color}`}>
                          {item.icon}
                        </span>
                        {item.label}
                      </div>
                      <span>{item.value}</span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Saúde do pipeline</CardTitle>
                <CardDescription>Taxas de processamento em tempo quase real.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <ProgressItem label="Concluídos" value={completionRate} color="bg-emerald-500" />
                <ProgressItem label="Processando" value={processingRate} color="bg-sky-500" />
                <ProgressItem label="Falhas" value={failureRate} color="bg-rose-500" />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Último upload</CardTitle>
                <CardDescription>Acompanhe o item mais recente enviado.</CardDescription>
              </CardHeader>
              <CardContent>
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
              </CardContent>
            </Card>
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-3xl border border-border/60 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-6 text-white shadow-lg md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-white/70">Painel pessoal</p>
          <h1 className="text-3xl font-semibold">Bem-vindo de volta, {user?.email}</h1>
          <p className="text-sm text-white/70">Centralize uploads, acompanhe o progresso e revisite insights em um único lugar.</p>
        </div>
        <div className="flex flex-col gap-2 text-sm">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-300" />
            <span>{stats.completed} arquivos concluídos</span>
          </div>
          <div className="flex items-center gap-2">
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
      {renderContent()}
    </div>
  );
};

export default DashboardPage;
