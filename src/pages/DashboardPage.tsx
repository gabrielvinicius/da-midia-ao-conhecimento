import * as React from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import { MediaCard } from "../features/media/components/MediaCard";
import { useMediaList } from "../features/media/hooks/useMedia";
import { useAuth } from "../contexts/AuthContext";
import { Upload, BarChart3, FileText, Video, Music, RefreshCw } from "lucide-react";

const DashboardPage = () => {
  const { data: media, isLoading, isError, error, refetch } = useMediaList();
  const { user } = useAuth();

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

  const renderStatsCards = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total de Arquivos</CardTitle>
          <FileText className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.total}</div>
          <p className="text-xs text-muted-foreground">
            {stats.processing > 0 && `${stats.processing} processando`}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Vídeos</CardTitle>
          <Video className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.videos}</div>
          <p className="text-xs text-muted-foreground">
            Arquivos de vídeo
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Áudios</CardTitle>
          <Music className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.audios}</div>
          <p className="text-xs text-muted-foreground">
            Arquivos de áudio
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Textos</CardTitle>
          <FileText className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.texts}</div>
          <p className="text-xs text-muted-foreground">
            PDFs e documentos
          </p>
        </CardContent>
      </Card>
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
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Seus Arquivos</h2>
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
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {media.map((item) => (
              <MediaCard key={item.id} media={item} />
            ))}
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Bem-vindo, {user?.email}! Gerencie seus arquivos de mídia e visualize análises.
          </p>
        </div>
        <Button asChild>
          <Link to="/analytics">
            <BarChart3 className="mr-2 h-4 w-4" />
            Ver Análises
          </Link>
        </Button>
      </div>
      {renderContent()}
    </div>
  );
};

export default DashboardPage;
