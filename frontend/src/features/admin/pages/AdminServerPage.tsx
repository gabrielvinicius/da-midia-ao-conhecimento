import type { ReactNode } from "react";
import { Cpu, HardDrive, MemoryStick, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";
import { useServerStatus } from "../hooks/useAdminQueries";

const PRESSURE: Record<string, { label: string; tone: string }> = {
  low: { label: "Carga normal", tone: "bg-emerald-100 text-emerald-800" },
  moderate: { label: "Carga moderada", tone: "bg-sky-100 text-sky-800" },
  high: { label: "Carga alta", tone: "bg-amber-100 text-amber-800" },
  critical: { label: "Capacidade crítica", tone: "bg-rose-100 text-rose-800" },
};

const SERVICES: { key: string; label: string; detail: string }[] = [
  { key: "database", label: "Banco de dados", detail: "PostgreSQL com pgvector" },
  { key: "redis", label: "Redis", detail: "Fila de tarefas e avisos" },
  { key: "ollama", label: "Ollama", detail: "Modelo de linguagem (resumo, capítulos, perguntas)" },
];

/** Barra de uso: verde até 70%, âmbar até 90%, vermelha acima. */
const Usage = ({ label, percent, detail, icon }: { label: string; percent: number | null; detail: string; icon: ReactNode }) => {
  const value = percent === null ? 0 : Math.min(100, Math.max(0, percent));
  const color = value > 90 ? "bg-rose-500" : value > 70 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <Card className="border-[#ede4d5] p-4">
      <p className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        {icon}
        {label}
      </p>
      <p className="mt-1 text-3xl font-semibold">{percent === null ? "—" : `${Math.round(value)}%`}</p>
      <div
        className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100"
        role="progressbar"
        aria-label={label}
        aria-valuenow={Math.round(value)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={cn("h-full rounded-full", color)} style={{ width: `${value}%` }} />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{detail}</p>
    </Card>
  );
};

const Dot = ({ ok }: { ok: boolean }) => (
  <span className={cn("inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full", ok ? "bg-emerald-500" : "bg-rose-500")} aria-hidden />
);

export const AdminServerPage = () => {
  const { data, isLoading, isError, refetch, isFetching } = useServerStatus();

  if (isError && !data) {
    return (
      <ErrorState
        title="Não foi possível ler o servidor"
        message="Verifique a conexão com o servidor e tente novamente."
        onRetry={() => refetch()}
      />
    );
  }

  const gpu = data?.gpu ?? null;
  const pressure = PRESSURE[data?.pressure ?? "low"] ?? PRESSURE.low;
  const gb = (mb: number) => (mb / 1024).toFixed(1).replace(".", ",");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="flex flex-wrap items-center gap-3 text-2xl font-semibold">
            Servidor
            {data && <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-medium", pressure.tone)}>{pressure.label}</span>}
          </h1>
          <p className="text-sm text-muted-foreground">Uso da máquina e se cada serviço responde. Atualiza a cada 15 segundos.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={cn("mr-2 h-4 w-4", isFetching && "animate-spin")} />
          Atualizar
        </Button>
      </div>

      {isLoading || !data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Usage
            label="Memória da GPU"
            percent={gpu ? (gpu.memory_used_mb / gpu.memory_total_mb) * 100 : null}
            detail={gpu ? `${gb(gpu.memory_used_mb)} de ${gb(gpu.memory_total_mb)} GB (placa inteira)` : "Sem leitura: o worker pesado está parado?"}
            icon={<HardDrive className="h-4 w-4" />}
          />
          <Usage
            label="Uso da GPU"
            percent={gpu ? gpu.utilization_percent : null}
            detail={gpu ? "Transcrição, visão e modelo de linguagem" : "Sem leitura recente"}
            icon={<HardDrive className="h-4 w-4" />}
          />
          <Usage
            label="Processador"
            percent={data.cpu_percent}
            detail={`${data.cpu_count} núcleos`}
            icon={<Cpu className="h-4 w-4" />}
          />
          <Usage
            label="Memória"
            percent={data.ram_total_gb ? (data.ram_used_gb / data.ram_total_gb) * 100 : null}
            detail={`${String(data.ram_used_gb).replace(".", ",")} de ${String(data.ram_total_gb).replace(".", ",")} GB`}
            icon={<MemoryStick className="h-4 w-4" />}
          />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-[#ede4d5]">
          <CardHeader>
            <CardTitle className="text-base">Serviços</CardTitle>
            <CardDescription>Se cada um respondeu na última verificação.</CardDescription>
          </CardHeader>
          <CardContent>
            {!data ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <ul className="space-y-3 text-sm">
                {SERVICES.map((service) => {
                  const ok = data.services[service.key] ?? false;
                  return (
                    <li key={service.key} className="flex items-start gap-3">
                      <span className="mt-1.5">
                        <Dot ok={ok} />
                      </span>
                      <div>
                        <p className="font-medium">
                          {service.label} <span className="font-normal text-muted-foreground">· {ok ? "respondendo" : "sem resposta"}</span>
                        </p>
                        <p className="text-xs text-muted-foreground">{service.detail}</p>
                      </div>
                    </li>
                  );
                })}
                <li className="flex items-start gap-3">
                  <span className="mt-1.5">
                    <Dot ok={data.workers.length >= 2} />
                  </span>
                  <div>
                    <p className="font-medium">
                      Workers do Celery{" "}
                      <span className="font-normal text-muted-foreground">
                        · {data.workers.length === 0 ? "nenhum respondeu" : `${data.workers.length} respondendo`}
                      </span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      São dois: o pesado (GPU: transcrição e análise) e o leve (verificações periódicas).
                    </p>
                  </div>
                </li>
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="border-[#ede4d5]">
          <CardHeader>
            <CardTitle className="text-base">Modelos carregados no Ollama</CardTitle>
            <CardDescription>Ocupam a GPU até 5 minutos depois do último uso.</CardDescription>
          </CardHeader>
          <CardContent>
            {!data ? (
              <Skeleton className="h-16 w-full" />
            ) : data.loaded_models.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {data.services.ollama ? "Nenhum modelo na memória agora." : "O Ollama não respondeu."}
              </p>
            ) : (
              <ul className="space-y-1 text-sm">
                {data.loaded_models.map((model) => (
                  <li key={model} className="font-mono">
                    {model}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
