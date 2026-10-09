import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { MessageSquare, PencilLine, Star } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import type { QualityReport } from "../api";
import { useQualityReport } from "../hooks/useAdminQueries";

const percent = (part: number, whole: number) => (whole ? Math.round((part / whole) * 100) : 0);

const Bar = ({ label, part, whole, unit }: { label: string; part: number; whole: number; unit: string }) => (
  <div>
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <span className="font-medium text-slate-900">{label}</span>
      <span className="text-muted-foreground">
        {part} de {whole} {unit} · <span className="font-semibold text-slate-900">{percent(part, whole)}%</span>
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

const Stars = ({ score }: { score: number }) => (
  <span className="text-amber-500" aria-label={`${score} de 5`}>
    {"★".repeat(score)}
    <span className="text-slate-300">{"★".repeat(Math.max(0, 5 - score))}</span>
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
  const maxRating = Math.max(1, ...Object.values(data.ratings));
  return (
    <>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <Kpi title="Análises" value={String(data.analyses)} detail="Mídias com análise gravada" icon={<PencilLine className="h-4 w-4" />} />
        <Kpi
          title="Nota média"
          value={data.rating_average === null ? "—" : data.rating_average.toFixed(1).replace(".", ",")}
          detail={data.rating_count ? `${data.rating_count} avaliações, de 1 a 5` : "Nenhuma avaliação ainda"}
          icon={<Star className="h-4 w-4" />}
        />
        <Kpi
          title="Resumos corrigidos"
          value={`${percent(data.corrected["resumo"] ?? 0, data.analyses)}%`}
          detail={`${data.corrected["resumo"] ?? 0} de ${data.analyses} análises`}
          icon={<PencilLine className="h-4 w-4" />}
        />
        <Kpi
          title="Trechos corrigidos"
          value={`${percent(data.segments_corrected, data.segments_total)}%`}
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
            <CardTitle className="text-base">Notas dadas</CardTitle>
            <CardDescription>Avaliações das análises pelos próprios usuários.</CardDescription>
          </CardHeader>
          <CardContent>
            {data.rating_count === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma avaliação ainda.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {[5, 4, 3, 2, 1].map((score) => {
                  const count = data.ratings[String(score)] ?? 0;
                  return (
                    <li key={score} className="flex items-center gap-3">
                      <span className="w-20 flex-shrink-0">
                        <Stars score={score} />
                      </span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                        <div className="h-full rounded-full bg-amber-400" style={{ width: `${(count / maxRating) * 100}%` }} />
                      </div>
                      <span className="w-8 text-right tabular-nums text-muted-foreground">{count}</span>
                    </li>
                  );
                })}
              </ul>
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
                      <Stars score={c.score} />
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
          Medida pelo uso real: o que os usuários corrigiram na saída da IA e as notas que deram.
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
