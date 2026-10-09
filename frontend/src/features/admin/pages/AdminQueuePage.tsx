import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Clock, FileText, Loader2, Music, RefreshCw, Sparkles, Video } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";
import type { QueueItem } from "../api";
import { useProcessingQueue } from "../hooks/useAdminQueries";
import { formatElapsed } from "@/lib/processingLabels";

const STAGES: Record<QueueItem["status"], { label: string; detail: string; icon: ReactNode; tone: string }> = {
  uploaded: {
    label: "Aguardando",
    detail: "Enviada, esperando o worker",
    icon: <Clock className="h-4 w-4" />,
    tone: "bg-slate-100 text-slate-700",
  },
  processing: {
    label: "Transcrevendo",
    detail: "Transcrição, descrição dos quadros ou extração do texto",
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    tone: "bg-sky-100 text-sky-800",
  },
  analyzing: {
    label: "Analisando",
    detail: "Temas, resumo, capítulos e perguntas",
    icon: <Sparkles className="h-4 w-4" />,
    tone: "bg-violet-100 text-violet-800",
  },
};

const BROKER_QUEUES: { key: string; label: string }[] = [
  { key: "transcription_fast_lane", label: "Transcrição (arquivos curtos, passam à frente)" },
  { key: "transcription_queue", label: "Transcrição" },
  { key: "text_analysis_queue", label: "Análise e extração de texto" },
  { key: "celery", label: "Manutenção (verificações periódicas)" },
];

const TYPE_ICONS: Record<string, ReactNode> = {
  video: <Video className="h-4 w-4" />,
  audio: <Music className="h-4 w-4" />,
  text: <FileText className="h-4 w-4" />,
};

const QueueRow = ({ item }: { item: QueueItem }) => {
  const stage = STAGES[item.status] ?? STAGES.uploaded;
  return (
    <li className={cn("flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:gap-4", item.stuck && "bg-amber-50/60 -mx-4 px-4 sm:-mx-6 sm:px-6")}>
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <span
          className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-slate-200 text-xs font-semibold text-slate-600"
          aria-label={`Posição ${item.position}`}
        >
          {item.position}
        </span>
        <div className="min-w-0">
          <Link
            to={`/media/${item.media_id}`}
            className="flex items-center gap-1.5 font-medium text-slate-900 [overflow-wrap:anywhere] hover:underline"
          >
            <span className="flex-shrink-0 text-muted-foreground">{TYPE_ICONS[item.media_type]}</span>
            {item.filename || item.media_id}
          </Link>
          <p className="text-xs text-muted-foreground [overflow-wrap:anywhere]">
            {item.owner_email ?? "dono desconhecido"} · enviada{" "}
            {formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: ptBR })}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 pl-10 sm:pl-0">
        <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium", stage.tone)} title={stage.detail}>
          {stage.icon}
          {stage.label}
        </span>
        <span className="text-xs text-muted-foreground" title={new Date(item.stage_since).toLocaleString("pt-BR")}>
          há {formatElapsed(item.stage_seconds)}
        </span>
        {item.stuck && (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
            <AlertTriangle className="h-3.5 w-3.5" />
            Parece parada
          </span>
        )}
      </div>
    </li>
  );
};

export const AdminQueuePage = () => {
  const { data, isLoading, isError, refetch, isFetching } = useProcessingQueue();

  if (isError && !data) {
    return (
      <ErrorState
        title="Não foi possível carregar a fila"
        message="Verifique a conexão com o servidor e tente novamente."
        onRetry={() => refetch()}
      />
    );
  }

  const items = data?.items ?? [];
  const stuck = items.filter((i) => i.stuck).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Fila de processamento</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            A GPU processa uma mídia por vez; as demais esperam na ordem de chegada (arquivos curtos passam à frente).
            A tela se atualiza a cada 10 segundos.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={cn("mr-2 h-4 w-4", isFetching && "animate-spin")} />
          Atualizar
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        {(Object.keys(STAGES) as QueueItem["status"][]).map((status) => (
          <Card key={status} className="border-[#ede4d5] p-3 sm:p-4">
            <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground sm:text-sm">
              <span className="hidden sm:inline">{STAGES[status].icon}</span>
              {STAGES[status].label}
            </p>
            {isLoading ? (
              <Skeleton className="mt-2 h-7 w-10" />
            ) : (
              <p className="mt-1 text-2xl font-semibold sm:text-3xl">{data?.counts[status] ?? 0}</p>
            )}
            <p className="mt-1 hidden text-xs text-muted-foreground sm:block">{STAGES[status].detail}</p>
          </Card>
        ))}
      </div>

      {stuck > 0 && (
        <div className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" role="status">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p>
            {stuck === 1 ? "1 mídia está" : `${stuck} mídias estão`} na mesma etapa há mais tempo que o normal. Confira se os
            workers estão rodando (<code>docker compose logs worker-heavy</code>) e abra a mídia para ver o que aconteceu.
          </p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="border-[#ede4d5] lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Mídias em andamento</CardTitle>
            <CardDescription>Da mais antiga para a mais nova, com o tempo na etapa atual.</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            ) : items.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Nenhuma mídia na fila: tudo processado.</p>
            ) : (
              <>
                <ul className="divide-y divide-slate-100">
                  {items.map((item) => (
                    <QueueRow key={item.media_id} item={item} />
                  ))}
                </ul>
                {data?.truncated && (
                  <p className="mt-3 text-xs text-muted-foreground">Mostrando as {items.length} mais antigas.</p>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-[#ede4d5]">
          <CardHeader>
            <CardTitle className="text-base">Tarefas no Celery</CardTitle>
            <CardDescription>Esperando um worker livre, por fila.</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : data?.broker ? (
              <ul className="space-y-2 text-sm">
                {BROKER_QUEUES.map(({ key, label }) => (
                  <li key={key} className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-semibold tabular-nums">{data.broker?.[key] ?? 0}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">Não foi possível ler as filas no Redis.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
