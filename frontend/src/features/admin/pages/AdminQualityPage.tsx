import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { MessageSquare, PencilLine, ThumbsDown, ThumbsUp } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import type { QualityReport } from "../api";
import { useQualityReport } from "../hooks/useAdminQueries";

const percent = (part: number, whole: number) => (whole ? Math.round((part / whole) * 100) : 0);
/** "<1%" quando há correção mas ela arredonda para zero (1 de 3.042 trechos não é "nenhum"). */
const percentLabel = (part: number, whole: number) => (part > 0 && percent(part, whole) === 0 ? "<1%" : `${percent(part, whole)}%`);

const Bar = ({ label, part, whole, unit }: { label: string; part: number; whole: number; unit: string }) => (
  <div>
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <span className="font-medium text-slate-900">{label}</span>
      <span className="text-muted-foreground">
        {part} de {whole} {unit} · <span className="font-semibold text-slate-900">{percentLabel(part, whole)}</span>
      </span>
    </div>
    <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label={label} aria-valuenow={percent(part, whole)} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-full rounded-full bg-amber-500" style={{ width: `${percent(part, whole)}%` }} />
    </div>
  </div>
);

const Kpi = ({ title, value, detail, icon }: { title: string; value: string; detail: string; icon: ReactNode }) => (
  <Card className="border-[#ede4d5] p-4">
    <p className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
      {icon}
      {title}
    </p>
    <p className="mt-1 text-3xl font-semibold">{value}</p>
    <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
  </Card>
);

/** O resumo é avaliado pelo polegar: 1 (útil) ou -1 (não foi útil). */
const Verdict = ({ score }: { score: number }) =>
  score > 0 ? (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
      <ThumbsUp className="h-3.5 w-3.5" /> Útil
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-700">
      <ThumbsDown className="h-3.5 w-3.5" /> Não foi útil
    </span>
  );

const MediaName = ({ id, name }: { id: string | null; name: string | null }) =>
  id && name ? (
    <Link to={`/media/${id}`} className="font-medium text-slate-900 [overflow-wrap:anywhere] hover:underline">
      {name}
    </Link>
  ) : (
    <span className="text-muted-foreground">Mídia excluída</span>
  );

const Content = ({ data }: { data: QualityReport }) => {
  const correctedAny = data.recent_corrections.length;
  const rated = data.useful + data.not_useful;
  return (
    <>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <Kpi title="Análises" value={String(data.analyses)} detail="Mídias com análise gravada" icon={<PencilLine className="h-4 w-4" />} />
        <Kpi
          title="Resumos úteis"
          value={data.useful_share === null ? "—" : `${Math.round(data.useful_share)}%`}
          detail={rated ? `${data.useful} de ${rated} avaliações` : "Nenhuma avaliação ainda"}
          icon={<ThumbsUp className="h-4 w-4" />}
        />
        <Kpi
          title="Resumos corrigidos"
          value={percentLabel(data.corrected["resumo"] ?? 0, data.analyses)}
          detail={`${data.corrected["resumo"] ?? 0} de ${data.analyses} análises`}
          icon={<PencilLine className="h-4 w-4" />}
        />
        <Kpi
          title="Trechos corrigidos"
          value={percentLabel(data.segments_corrected, data.segments_total)}
          detail={`${data.segments_corrected} de ${data.segments_total} trechos de transcrição`}
          icon={<MessageSquare className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-[#ede4d5]">
          <CardHeader>
            <CardTitle className="text-base">O que os usuários corrigiram</CardTitle>
            <CardDescription>Quanto da saída da IA precisou de ajuste. A versão da IA fica guardada na primeira correção.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Bar label="Resumo" part={data.corrected["resumo"] ?? 0} whole={data.analyses} unit="análises" />
            <Bar label="Títulos dos temas" part={data.corrected["temas"] ?? 0} whole={data.analyses} unit="análises" />
            <Bar label="Capítulos" part={data.corrected["capítulos"] ?? 0} whole={data.analyses} unit="análises" />
            <Bar label="Perguntas de revisão" part={data.corrected["perguntas"] ?? 0} whole={data.analyses} unit="análises" />
            <Bar label="Transcrição" part={data.corrected_transcriptions} whole={data.transcriptions} unit="transcrições" />
          </CardContent>
        </Card>

        <Card className="border-[#ede4d5]">
          <CardHeader>
            <CardTitle className="text-base">O resumo foi útil?</CardTitle>
            <CardDescription>Respostas dos usuários pelo polegar, abaixo de cada resumo.</CardDescription>
          </CardHeader>
          <CardContent>
            {rated === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma avaliação ainda.</p>
            ) : (
              <div className="space-y-4">
                <Bar label="Útil" part={data.useful} whole={rated} unit="avaliações" />
                <Bar label="Não foi útil" part={data.not_useful} whole={rated} unit="avaliações" />
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-[#ede4d5]">
          <CardHeader>
            <CardTitle className="text-base">Comentários recentes</CardTitle>
            <CardDescription>O que os usuários escreveram ao avaliar.</CardDescription>
          </CardHeader>
          <CardContent>
            {data.recent_comments.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum comentário ainda.</p>
            ) : (
              <ul className="divide-y divide-slate-100 text-sm">
                {data.recent_comments.map((c, i) => (
                  <li key={i} className="py-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <MediaName id={c.media_id} name={c.filename} />
                      <Verdict score={c.score} />
                    </div>
                    <p className="mt-1 text-slate-700">“{c.comment}”</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="border-[#ede4d5]">
          <CardHeader>
            <CardTitle className="text-base">Análises corrigidas</CardTitle>
            <CardDescription>As mais recentes e o que foi ajustado em cada uma.</CardDescription>
          </CardHeader>
          <CardContent>
            {correctedAny === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma análise corrigida ainda.</p>
            ) : (
              <ul className="divide-y divide-slate-100 text-sm">
                {data.recent_corrections.map((c, i) => (
                  <li key={i} className="flex flex-wrap items-center justify-between gap-2 py-3">
                    <MediaName id={c.media_id} name={c.filename} />
                    <span className="flex flex-wrap gap-1">
                      {c.parts.map((part) => (
                        <span key={part} className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
                          {part}
                        </span>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export const AdminQualityPage = () => {
  const { data, isLoading, isError, refetch } = useQualityReport();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Qualidade da IA</h1>
        <p className="text-sm text-muted-foreground">
          Medida pelo uso real: o que os usuários corrigiram na saída da IA e se acharam o resumo útil.
        </p>
      </div>
      {isLoading ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : isError || !data ? (
        <ErrorState title="Não foi possível carregar o relatório" message="Tente novamente em instantes." onRetry={() => refetch()} />
      ) : (
        <Content data={data} />
      )}
    </div>
  );
};
