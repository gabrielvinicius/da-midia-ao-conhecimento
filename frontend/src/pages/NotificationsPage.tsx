import * as React from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { AlertTriangle, CheckCheck, CheckCircle2, Info } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useWebSocket } from "@/contexts/WebSocketContext";
import { friendlyError } from "@/features/media/lib/friendlyError";
import { listNotifications } from "@/features/notifications/api";
import { cn } from "@/lib/utils";
import type { Notification } from "@/types";

const FAILURE_EVENTS = new Set(["TranscriptionFailed", "MediaProcessingFailed", "MediaFailed", "AnalysisFailed"]);
const SUCCESS_EVENTS = new Set(["TranscriptionCompleted", "AnalysisCompleted"]);

const kindOf = (n: Notification) => {
  const event = String(n.variables?.evento ?? "");
  if (FAILURE_EVENTS.has(event)) return "failure";
  if (SUCCESS_EVENTS.has(event)) return "success";
  return "info";
};

const ICONS = {
  failure: <AlertTriangle className="h-4 w-4 text-rose-600" />,
  success: <CheckCircle2 className="h-4 w-4 text-emerald-600" />,
  info: <Info className="h-4 w-4 text-sky-600" />,
};

/**
 * Todos os avisos, não só os últimos do sino: o que terminou, o que falhou e
 * por quê, com o link para a mídia.
 */
const NotificationsPage = () => {
  const [unreadOnly, setUnreadOnly] = React.useState(false);
  const { markAsRead, markAllAsRead } = useWebSocket();
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["notifications-page", unreadOnly],
    queryFn: () => listNotifications({ limit: 100, unread: unreadOnly }),
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["notifications-page"] });
  const readOne = async (n: Notification) => {
    if (n.read) return;
    await markAsRead(n.id);
    refresh();
  };
  const readAll = async () => {
    await markAllAsRead();
    refresh();
  };

  const items = data ?? [];
  const unread = items.filter((n) => !n.read).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Avisos</h1>
          <p className="text-sm text-muted-foreground">O andamento das suas mídias: o que terminou e o que precisa de atenção.</p>
        </div>
        <Button variant="outline" size="sm" onClick={readAll} disabled={unread === 0}>
          <CheckCheck className="mr-2 h-4 w-4" />
          Marcar todos como lidos
        </Button>
      </div>

      <Card className="border-[#ede4d5] p-4 sm:p-6">
        <div className="flex gap-2" role="group" aria-label="Quais avisos">
          {[
            { value: false, label: "Todos" },
            { value: true, label: "Não lidos" },
          ].map((option) => (
            <button
              key={option.label}
              type="button"
              aria-pressed={unreadOnly === option.value}
              onClick={() => setUnreadOnly(option.value)}
              className={cn(
                "rounded-full border px-3 py-1 text-sm",
                unreadOnly === option.value ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 text-slate-700 hover:border-slate-400",
              )}
            >
              {option.label}
            </button>
          ))}
        </div>

        {isLoading ? (
          <div className="mt-4 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : isError ? (
          <ErrorState title="Não foi possível carregar os avisos" message="Tente novamente em instantes." onRetry={() => refetch()} />
        ) : items.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            {unreadOnly ? "Nenhum aviso não lido." : "Nenhum aviso ainda. Eles aparecem quando suas mídias terminam de processar."}
          </p>
        ) : (
          <ul className="mt-2 divide-y divide-slate-100">
            {items.map((n) => {
              const kind = kindOf(n);
              const mediaId = typeof n.variables?.media_id === "string" ? n.variables.media_id : null;
              const error = typeof n.variables?.erro === "string" ? n.variables.erro : null;
              return (
                <li key={n.id} className="flex gap-3 py-4" onClick={() => readOne(n)}>
                  <span className="mt-0.5 flex-shrink-0">{ICONS[kind]}</span>
                  <div className="min-w-0 flex-1">
                    <p className={cn("text-sm", n.read ? "text-muted-foreground" : "font-medium text-slate-900")}>{n.content}</p>
                    {kind === "failure" && error && (
                      <p className="mt-0.5 text-xs text-rose-700" title={error}>
                        {friendlyError(error)}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(n.created_at), { addSuffix: true, locale: ptBR })}
                      {mediaId && (
                        <>
                          {" · "}
                          <Link to={`/media/${mediaId}`} className="font-medium text-slate-900 underline-offset-2 hover:underline">
                            Abrir mídia
                          </Link>
                        </>
                      )}
                    </p>
                  </div>
                  {!n.read && <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-sky-500" aria-label="Não lido" />}
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
};

export default NotificationsPage;
