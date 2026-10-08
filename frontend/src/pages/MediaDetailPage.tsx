import { useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { CalendarDays, Clock, FileText, Loader2, RefreshCw, ShieldAlert, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Markdown } from "@/components/ui/Markdown";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs, type TabItem } from "@/components/ui/Tabs";
import { PredictiveInsight } from "@/components/PredictiveInsight";
import { ProcessingTrace } from "@/components/ProcessingTrace";
import { useAuth } from "@/contexts/AuthContext";
import { requestScopedToken } from "@/features/authentication/api/scopedToken";
import { ExportMenu } from "@/features/media/components/ExportMenu";
import { MediaPlayer } from "@/features/media/components/MediaPlayer";
import { ScreenPanel } from "@/features/media/components/ScreenPanel";
import { useReprocessMediaMutation } from "@/features/media/hooks/useMediaMutations";
import { useMediaByIdQuery } from "@/features/media/hooks/useMediaQueries";
import {
  chaptersOf,
  questionsOf,
  screenMomentsOf,
  summaryTitle,
  topicsInOrder,
} from "@/features/media/lib/analysisContent";
import { studyGuideMarkdown } from "@/features/media/lib/exporters";
import { friendlyError } from "@/features/media/lib/friendlyError";
import { getStatusToken } from "@/features/media/lib/status-helpers";
import { SentimentResultPanel } from "@/features/sentiment_analysis/components/SentimentResultPanel";
import { ChapterNav } from "@/features/summarization/components/ChapterNav";
import type { GroundingReport } from "@/features/summarization/components/GroundingNotice";
import { StudyAids } from "@/features/summarization/components/StudyAids";
import { SummaryPanel, genreLabel } from "@/features/summarization/components/SummaryPanel";
import { useTextAnalysisByMediaIdQuery } from "@/features/summarization/hooks/useAnalysisQuery";
import { TopicModelingResultPanel } from "@/features/topic_modeling/components/TopicModelingResultPanel";
import { InteractiveTranscriptionPanel } from "@/features/transcription/components/InteractiveTranscriptionPanel";
import { useTranscription } from "@/features/transcription/hooks/useTranscription";
import { buildApiUrl } from "@/lib/api";
import { formatClock } from "@/lib/time";
import { MediaStatus, MediaType, UserRole, isInProgress } from "@/types";

const MEDIA_TYPE_LABELS: Record<string, string> = { video: "Vídeo", audio: "Áudio", text: "Documento", image: "Imagem" };

/**
 * Página de uma mídia: o reprodutor e os capítulos ficam à esquerda (fixos ao
 * rolar), e o que a análise extraiu fica em abas à direita (resumo, estudo,
 * transcrição, temas e o que aparecia na tela). Antes, tudo ficava empilhado
 * numa página de ~12 telas, com os capítulos no fim.
 */
const MediaDetailPage = () => {
  const { id = "" } = useParams<{ id: string }>();
  // ?t=SEGUNDOS: a busca abre a mídia no momento do trecho; ?aba=: a aba aberta.
  const [searchParams, setSearchParams] = useSearchParams();
  const startAt = Number(searchParams.get("t")) || undefined;
  const { user } = useAuth();
  const playerRef = useRef<HTMLMediaElement>(null);
  const [currentTime, setCurrentTime] = useState(0);

  const { data: media, isLoading, isError } = useMediaByIdQuery(id);
  const transcriptionQuery = useTranscription(id);
  const analysisQuery = useTextAnalysisByMediaIdQuery(id);
  const reprocess = useReprocessMediaMutation();
  const isPlayable = media?.media_type === MediaType.AUDIO || media?.media_type === MediaType.VIDEO;
  // Token só desta mídia, válido por horas: a URL do vídeo não muda no meio da reprodução.
  const { data: streamToken } = useQuery({
    queryKey: ["stream-token", id],
    queryFn: () => requestScopedToken("media_stream", id),
    enabled: Boolean(id && isPlayable),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  if (!id) return <p className="text-destructive">Nenhuma mídia informada.</p>;
  if (isLoading) return <PageSkeleton />;
  if (isError || !media) return <p className="text-destructive">Não foi possível carregar a mídia.</p>;

  const analysis = analysisQuery.data;
  const transcription = transcriptionQuery.data;
  const canEdit = user?.role === UserRole.ADMIN || media.user_id === user?.id;
  const chapters = chaptersOf(analysis);
  const questions = questionsOf(analysis);
  const topics = topicsInOrder(analysis);
  const screen = screenMomentsOf(analysis);
  const duration =
    transcription?.duration ?? media.duration ?? transcription?.segments?.[transcription.segments.length - 1]?.end ?? null;
  const title = summaryTitle(analysis?.summary) ?? media.filename ?? media.id;
  const status = getStatusToken(media.status);
  const genre = genreLabel(analysis?.diagnostics?.genre);
  const grounding = analysis?.diagnostics?.grounding as GroundingReport | undefined;
  const exportInput = { media, analysis, transcription };

  const seek = isPlayable
    ? (time: number) => {
        const player = playerRef.current;
        if (!player) return;
        player.currentTime = time;
        void player.play().catch(() => undefined);
      }
    : undefined;

  const tabs: TabItem[] = [
    { id: "resumo", label: "Resumo" },
    { id: "estudo", label: "Estudo", count: questions.length || undefined },
    { id: "transcricao", label: isPlayable ? "Transcrição" : "Texto extraído" },
    { id: "temas", label: "Temas e tom", count: topics.length || undefined },
    ...(screen.length ? [{ id: "tela", label: "Na tela", count: screen.length }] : []),
  ];
  const requested = searchParams.get("aba");
  const activeTab = tabs.some((t) => t.id === requested) ? requested! : "resumo";
  const changeTab = (tab: string) =>
    setSearchParams(
      (params) => {
        params.set("aba", tab);
        return params;
      },
      { replace: true },
    );

  const streamUrl = streamToken
    ? buildApiUrl(`/media/${media.id}/stream?token=${encodeURIComponent(streamToken)}`) + (startAt ? "" : "#t=0.5")
    : "";
  const hasSideColumn = isPlayable || chapters.length > 0;

  return (
    <div className="mx-auto w-full min-w-0 max-w-[1400px] space-y-6 pb-16">
      <header className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 space-y-2">
            <h1 className="text-2xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-3xl">{title}</h1>
            {title !== media.filename && media.filename && (
              <p className="flex min-w-0 items-center gap-1.5 text-sm text-slate-500" title={media.filename}>
                <FileText className="h-3.5 w-3.5 shrink-0" />
                <span className="min-w-0 truncate">{media.filename}</span>
              </p>
            )}
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {canEdit && media.status === MediaStatus.FAILED && (
              <Button onClick={() => reprocess.mutate(media.id)} disabled={reprocess.isPending} variant="outline" size="sm" className="gap-2">
                {reprocess.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                {reprocess.isPending ? "Reprocessando..." : "Reprocessar"}
              </Button>
            )}
            <ExportMenu input={exportInput} onPrint={() => window.print()} />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
          <Badge className={status.badge}>{status.label}</Badge>
          {genre && <Badge variant="outline" title="Tipo de conteúdo identificado; orienta o que o resumo destaca.">{genre}</Badge>}
          <Badge variant="outline">{MEDIA_TYPE_LABELS[media.media_type] ?? media.media_type}</Badge>
          {duration ? (
            <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {formatClock(duration)}</span>
          ) : null}
          <span className="inline-flex items-center gap-1">
            <CalendarDays className="h-3.5 w-3.5" /> {format(new Date(media.created_at), "dd 'de' MMM 'de' yyyy", { locale: ptBR })}
          </span>
          {grounding?.checked ? <FidelityChip report={grounding} onClick={() => changeTab("resumo")} /> : null}
          <ProcessingTrace media={media} analysis={analysis} transcriptionStatus={transcription?.status} />
        </div>

        {media.status === MediaStatus.FAILED && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
            <p className="font-medium">{friendlyError(media.error_message)}</p>
            <p className="mt-1">{canEdit ? "Você pode tentar de novo com o botão Reprocessar." : "Peça ao dono da mídia para reprocessá-la."}</p>
            {media.error_message && (
              <details className="mt-2 text-xs text-red-700/80">
                <summary className="cursor-pointer">Detalhes técnicos</summary>
                <p className="mt-1 break-words font-mono">{media.error_message}</p>
              </details>
            )}
          </div>
        )}
      </header>

      <PredictiveInsight mediaId={id} isEnabled={media.status === MediaStatus.UPLOADED || isInProgress(media.status)} />

      <div className={hasSideColumn ? "grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]" : ""}>
        {hasSideColumn && (
          <aside className="space-y-4 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-y-auto">
            {isPlayable && (
              <div className="overflow-hidden rounded-2xl bg-black">
                {streamUrl ? (
                  <MediaPlayer
                    src={streamUrl}
                    mediaType={media.media_type as MediaType.AUDIO | MediaType.VIDEO}
                    playerRef={playerRef}
                    onTimeUpdate={setCurrentTime}
                    startAt={startAt}
                  />
                ) : (
                  <Skeleton className="aspect-video w-full" />
                )}
              </div>
            )}
            <ChapterNav chapters={chapters} currentTime={currentTime} duration={duration} onSeek={seek} />
            {analysis && (analysis.sentiment_items?.length ?? 0) > 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <h2 className="mb-2 text-sm font-semibold text-slate-900">Tom ao longo da gravação</h2>
                <SentimentResultPanel analysis={analysis} onSeek={seek} compact />
              </div>
            )}
          </aside>
        )}

        <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <Tabs tabs={tabs} active={activeTab} onChange={changeTab} label="Conteúdo extraído">
            {activeTab === "resumo" && (
              <SummaryPanel
                analysis={analysis}
                isLoading={analysisQuery.isLoading}
                isError={analysisQuery.isError}
                mediaStatus={media.status}
                onSeek={seek}
                canEdit={canEdit}
                hideTitle
              />
            )}
            {activeTab === "estudo" && <StudyAids analysis={analysis} onSeek={seek} canEdit={canEdit} />}
            {activeTab === "transcricao" && (
              <InteractiveTranscriptionPanel
                transcription={transcription}
                isLoading={transcriptionQuery.isLoading}
                currentTime={currentTime}
                onSeek={seek}
                canEdit={canEdit}
              />
            )}
            {activeTab === "temas" && (
              <div className="space-y-8">
                <TopicModelingResultPanel analysis={analysis} onSeek={seek} canEdit={canEdit} />
                <div>
                  <h3 className="mb-3 text-base font-semibold text-slate-900">Tom</h3>
                  <SentimentResultPanel analysis={analysis} onSeek={seek} />
                </div>
              </div>
            )}
            {activeTab === "tela" && <ScreenPanel analysis={analysis} onSeek={seek} />}
          </Tabs>
        </section>
      </div>

      {analysis?.summary &&
        createPortal(
          <article className="print-only">
            <Markdown text={studyGuideMarkdown(exportInput)} />
          </article>,
          document.body,
        )}
    </div>
  );
};

const FidelityChip = ({ report, onClick }: { report: GroundingReport; onClick: () => void }) => {
  const issues = report.unsupported.length + (report.gaps?.length ?? 0) + (report.number_issues?.length ?? 0);
  const Icon = issues ? ShieldAlert : ShieldCheck;
  return (
    <button
      type="button"
      onClick={onClick}
      title="Verificação automática do resumo contra a transcrição"
      className={
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium " +
        (issues ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-800")
      }
    >
      <Icon className="h-3.5 w-3.5" />
      {report.supported}/{report.checked} frases conferidas{issues ? ` · ${issues} a revisar` : ""}
    </button>
  );
};

const PageSkeleton = () => (
  <div className="mx-auto max-w-[1400px] space-y-6">
    <Skeleton className="h-32 w-full rounded-2xl" />
    <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <Skeleton className="aspect-video w-full rounded-2xl" />
      <Skeleton className="h-96 w-full rounded-2xl" />
    </div>
  </div>
);

export default MediaDetailPage;
