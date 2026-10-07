import { ShieldCheck, ShieldAlert } from "lucide-react";

export type GroundingReport = {
  checked: number;
  supported: number;
  ratio: number | null;
  threshold: number;
  unsupported: { text: string; best_score: number; closest_start: number | null }[];
  // Análises anteriores à verificação de cobertura e de números não têm estes campos.
  windows?: number;
  coverage?: number | null;
  gaps?: { start: number; end: number }[];
  number_issues?: { text: string; numbers: string[] }[];
};

const formatTime = (seconds: number | null) => {
  if (seconds == null) return null;
  const s = Math.floor(seconds);
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return s >= 3600 ? `${Math.floor(s / 3600)}:${mm}:${ss}` : `${mm}:${ss}`;
};

/**
 * Resultado da verificação automática de fidelidade (diagnostics.grounding):
 * frases do resumo sem trecho parecido na transcrição, partes da gravação que
 * o resumo não menciona e números que não aparecem no trecho do assunto. Vale
 * para a versão gerada pela IA; some quando o resumo foi corrigido pelo usuário.
 * Com ``truncated``, avisa que o resumo ficou incompleto (o modelo parou antes
 * do fim mesmo depois de continuar).
 */
export const GroundingNotice = ({
  report,
  truncated = false,
}: {
  report?: GroundingReport | null;
  truncated?: boolean;
}) => {
  if (!report || !report.checked) return null;
  const gaps = report.gaps ?? [];
  const numberIssues = report.number_issues ?? [];
  const allSupported = report.unsupported.length === 0;
  const clean = allSupported && gaps.length === 0 && numberIssues.length === 0 && !truncated;
  const Icon = clean ? ShieldCheck : ShieldAlert;

  return (
    <div
      className={`rounded-xl border p-3 text-sm ${
        clean ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"
      }`}
    >
      <p className="flex items-center gap-2 font-medium">
        <Icon className="h-4 w-4 shrink-0" />
        {allSupported
          ? `As ${report.checked} frases verificadas têm apoio na transcrição.`
          : `${report.supported} de ${report.checked} frases têm apoio na transcrição; confira as demais.`}
      </p>
      {truncated && (
        <p className="mt-1 text-xs font-medium">
          O resumo ficou incompleto: o modelo parou antes de terminar. Use os trechos do apêndice para o restante.
        </p>
      )}
      {!allSupported && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs">Frases sem trecho parecido na gravação</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
            {report.unsupported.map((item, index) => (
              <li key={index}>
                {item.text}
                {formatTime(item.closest_start) && (
                  <span className="text-amber-700"> (trecho mais próximo em {formatTime(item.closest_start)})</span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
      {gaps.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs">
            Partes da gravação que o resumo não menciona ({gaps.length})
          </summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
            {gaps.map((gap, index) => (
              <li key={index}>
                {formatTime(gap.start)} a {formatTime(gap.end)}
              </li>
            ))}
          </ul>
        </details>
      )}
      {numberIssues.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs">Números a conferir ({numberIssues.length})</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
            {numberIssues.map((item, index) => (
              <li key={index}>
                {item.text} <span className="text-amber-700">({item.numbers.join(", ")} não aparece no trecho do assunto)</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      <p className="mt-2 text-[11px] opacity-80">
        Verificação automática por semelhança de significado: aponta assuntos que não aparecem na gravação, partes
        longas que o resumo não menciona e números fora do trecho do assunto, mas não detecta um nome trocado.
      </p>
    </div>
  );
};
