import { ShieldCheck, ShieldAlert } from "lucide-react";

export type GroundingReport = {
  checked: number;
  supported: number;
  ratio: number | null;
  threshold: number;
  unsupported: { text: string; best_score: number; closest_start: number | null }[];
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
 * quantas frases do resumo têm um trecho parecido na transcrição, e quais
 * não têm, para o usuário conferir. Vale para a versão gerada pela IA; some
 * quando o resumo foi corrigido pelo usuário.
 */
export const GroundingNotice = ({ report }: { report?: GroundingReport | null }) => {
  if (!report || !report.checked) return null;
  const allSupported = report.unsupported.length === 0;
  const Icon = allSupported ? ShieldCheck : ShieldAlert;

  return (
    <div
      className={`rounded-xl border p-3 text-sm ${
        allSupported ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"
      }`}
    >
      <p className="flex items-center gap-2 font-medium">
        <Icon className="h-4 w-4 shrink-0" />
        {allSupported
          ? `As ${report.checked} frases verificadas têm apoio na transcrição.`
          : `${report.supported} de ${report.checked} frases têm apoio na transcrição; confira as demais.`}
      </p>
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
      <p className="mt-2 text-[11px] opacity-80">
        Verificação automática por semelhança de significado: aponta assuntos que não aparecem na gravação, mas
        não detecta um número ou nome trocado.
      </p>
    </div>
  );
};
