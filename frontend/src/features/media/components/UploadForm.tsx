import * as React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Link2,
  Loader2,
  Music,
  RotateCcw,
  Settings2,
  UploadCloud,
  Video,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Label } from "@/components/ui/Label";
import { cn } from "@/lib/utils";
import { getProviders, getUrlImportOptions, ProvidersResponse } from "../api";
import { isYoutubeLink, linkProblem, useUploadQueue, type UploadItem } from "../hooks/useUploadQueue";
import { ACCEPTED_EXTENSIONS, MAX_FILE_SIZE_MB, formatFileSize, type UploadKind } from "../uploadFile";
import { ProviderSelect } from "./ProviderSelect";

const KIND: Record<UploadKind, { label: string; icon: React.ReactNode; color: string }> = {
  video: { label: "Vídeo", icon: <Video className="h-5 w-5" />, color: "bg-violet-50 text-violet-700" },
  audio: { label: "Áudio", icon: <Music className="h-5 w-5" />, color: "bg-emerald-50 text-emerald-700" },
  text: { label: "Documento", icon: <FileText className="h-5 w-5" />, color: "bg-sky-50 text-sky-700" },
};

/**
 * Envio de mídias: arrastar e soltar (ou escolher) um ou vários arquivos,
 * que são enviados um por um, com o progresso e o resultado de cada um.
 */
export const UploadForm = () => {
  const queue = useUploadQueue();
  const [dragging, setDragging] = React.useState(false);
  const [chosenStorage, setChosenStorage] = React.useState<string | undefined>("local");
  const [transcriptionProvider, setTranscriptionProvider] = React.useState<string | undefined>();
  const inputRef = React.useRef<HTMLInputElement>(null);

  const providers = useQuery<ProvidersResponse>({
    queryKey: ["providers"],
    queryFn: getProviders,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  // A importação por link pode estar desligada no servidor: sem ela, o campo some.
  const urlImport = useQuery({
    queryKey: ["url-import-options"],
    queryFn: getUrlImportOptions,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  const [link, setLink] = React.useState("");
  const [linkError, setLinkError] = React.useState<string | null>(null);
  const stages = providers.isError ? undefined : providers.data?.stages;
  const storageOptions = React.useMemo(() => stages?.storage ?? [], [stages]);
  const transcriptionOptions = stages?.transcription ?? [];

  // O armazenamento escolhido precisa existir na lista do servidor; se não
  // existe, vale o primeiro da lista.
  const storageProvider =
    storageOptions.length && !storageOptions.some((p) => p.name === chosenStorage)
      ? storageOptions[0].name
      : chosenStorage;

  const waiting = queue.items.filter((i) => i.status === "waiting").length;
  const sent = queue.items.filter((i) => i.status === "sent");
  const hasSpeech = queue.items.some((i) => i.kind === "video" || i.kind === "audio");
  const finished = queue.items.length > 0 && !queue.running && waiting === 0;

  const onDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setDragging(false);
    if (event.dataTransfer.files?.length) queue.add(event.dataTransfer.files);
  };

  const addLink = () => {
    const problem = linkProblem(link);
    setLinkError(problem);
    if (problem) return;
    queue.addLink(link);
    setLink("");
  };

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!storageProvider || !waiting) return;
    void queue.start({ storageProvider, transcriptionProvider });
  };

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <label
        htmlFor="file"
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors",
          "focus-within:ring-2 focus-within:ring-amber-400 focus-within:ring-offset-2",
          dragging ? "border-amber-500 bg-amber-50" : "border-slate-300 bg-slate-50/60 hover:border-slate-400 hover:bg-slate-50",
        )}
      >
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-amber-600 shadow-xs">
          <UploadCloud className="h-6 w-6" />
        </span>
        <span className="text-base font-medium text-slate-900">
          {dragging ? "Solte os arquivos aqui" : "Arraste os arquivos para cá ou clique para escolher"}
        </span>
        <span className="max-w-md text-sm text-slate-500">
          Vídeos, áudios, PDFs, documentos do Word e imagens, até {MAX_FILE_SIZE_MB} MB cada. Pode enviar vários de uma vez.
        </span>
        <input
          ref={inputRef}
          id="file"
          type="file"
          multiple
          aria-label="Escolher arquivos"
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="sr-only"
          onChange={(e) => {
            if (e.target.files?.length) queue.add(e.target.files);
            e.target.value = ""; // permite escolher o mesmo arquivo de novo
          }}
        />
      </label>

      {urlImport.data?.enabled && (
        <div className="space-y-1.5">
          <Label htmlFor="media-link" className="text-sm text-slate-700">
            Ou importe por link
          </Label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Link2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                id="media-link"
                type="url"
                inputMode="url"
                placeholder="https://... (YouTube ou link direto para o arquivo)"
                value={link}
                onChange={(e) => {
                  setLink(e.target.value);
                  setLinkError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault(); // não envia o formulário
                    addLink();
                  }
                }}
                className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm outline-hidden focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <Button type="button" variant="outline" onClick={addLink} disabled={!link.trim()}>
              Adicionar
            </Button>
          </div>
          {linkError ? (
            <p className="text-xs text-red-700">{linkError}</p>
          ) : (
            <p className="text-xs text-slate-500">
              Vídeo do YouTube (até {urlImport.data.max_minutes} min) ou link direto para vídeo, áudio, PDF, documento ou imagem; links do Google Drive e do Dropbox precisam estar abertos a qualquer pessoa. Só use conteúdos que você tem direito de usar.
            </p>
          )}
        </div>
      )}

      {queue.items.length > 0 && (
        <ul className="space-y-2" aria-label="Arquivos para enviar">
          {queue.items.map((item) => (
            <QueueRow
              key={item.id}
              item={item}
              onRemove={() => queue.remove(item.id)}
              onRetry={() => queue.retry(item.id)}
              busy={queue.running}
            />
          ))}
        </ul>
      )}

      <details className="group rounded-xl border border-slate-200 bg-white">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium text-slate-700">
          <Settings2 className="h-4 w-4 text-slate-500" /> Opções avançadas
          <span className="ml-auto text-xs font-normal text-slate-400 group-open:hidden">Padrão do sistema</span>
        </summary>
        <div className="space-y-4 border-t border-slate-100 px-4 py-4 text-sm">
          {providers.isError && (
            <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800">
              Não foi possível carregar as opções do servidor. Você pode digitar os nomes.
            </p>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="storage-provider">Onde guardar os arquivos</Label>
            <ProviderSelect
              id="storage-provider"
              options={storageOptions}
              value={storageProvider}
              onChange={setChosenStorage}
              disabled={queue.running || providers.isLoading}
              fallbackPlaceholder="Nome do armazenamento"
            />
          </div>
          {hasSpeech && (
            <div className="space-y-1.5">
              <Label htmlFor="transcription-provider">Modelo de transcrição (vídeos e áudios)</Label>
              <ProviderSelect
                id="transcription-provider"
                options={transcriptionOptions}
                value={transcriptionProvider}
                onChange={setTranscriptionProvider}
                disabled={queue.running || providers.isLoading}
                allowAuto
                fallbackPlaceholder="Automático (ou digite o nome)"
              />
            </div>
          )}
        </div>
      </details>

      {finished && sent.length > 0 ? (
        <div className="space-y-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900" role="status">
          <p className="font-medium">
            {sent.length === 1 ? "Mídia enviada." : `${sent.length} mídias enviadas.`} O processamento segue em segundo plano;
            o sino avisa quando cada análise terminar.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button asChild size="sm">
              <Link to="/dashboard">Ver no painel</Link>
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={() => queue.clearFinished()}>
              Enviar outros
            </Button>
          </div>
        </div>
      ) : (
        <Button type="submit" className="w-full" size="lg" disabled={queue.running || !waiting || !storageProvider}>
          {queue.running ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Enviando...
            </>
          ) : waiting > 1 ? (
            `Enviar ${waiting} mídias`
          ) : (
            "Enviar"
          )}
        </Button>
      )}
    </form>
  );
};

const QueueRow = ({
  item,
  onRemove,
  onRetry,
  busy,
}: {
  item: UploadItem;
  onRemove: () => void;
  onRetry: () => void;
  busy: boolean;
}) => {
  const kind = item.kind ? KIND[item.kind] : null;
  return (
    <li className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3">
      <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", kind?.color ?? "bg-red-50 text-red-600")}>
        {item.url ? <Link2 className="h-5 w-5" /> : kind?.icon ?? <AlertCircle className="h-5 w-5" />}
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <p className="truncate text-sm font-medium text-slate-900" title={item.name}>
          {item.name}
        </p>
        <p className="text-xs text-slate-500">
          {item.url
            ? item.status === "sending"
              ? `Baixando ${isYoutubeLink(item.url) ? "do YouTube" : "o arquivo"}... pode levar alguns minutos`
              : item.status === "sent"
                ? `${kind ? kind.label : "Arquivo"} importado por link`
                : isYoutubeLink(item.url) ? "Vídeo do YouTube" : "Link direto"
            : `${kind ? `${kind.label} · ` : ""}${formatFileSize(item.file?.size ?? 0)}${item.status === "sending" ? ` · ${item.progress}%` : ""}`}
        </p>
        {item.status === "sending" && (
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={item.url ? undefined : item.progress} aria-valuemin={0} aria-valuemax={100} aria-label={`Envio de ${item.name}`}>
            {item.url ? (
              <div className="h-full w-1/3 animate-pulse rounded-full bg-amber-500" />
            ) : (
              <div className="h-full bg-amber-500 transition-all duration-150" style={{ width: `${item.progress}%` }} />
            )}
          </div>
        )}
        {item.message && <p className="text-xs text-red-700">{item.message}</p>}
      </div>
      <RowStatus item={item} onRemove={onRemove} onRetry={onRetry} busy={busy} />
    </li>
  );
};

const RowStatus = ({ item, onRemove, onRetry, busy }: { item: UploadItem; onRemove: () => void; onRetry: () => void; busy: boolean }) => {
  if (item.status === "sending") return <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-600" aria-label="Enviando" />;
  if (item.status === "sent") {
    return (
      <span className="flex shrink-0 items-center gap-2 text-xs text-emerald-700">
        <CheckCircle2 className="h-4 w-4" />
        {item.mediaId ? (
          <Link to={`/media/${item.mediaId}`} className="font-medium underline-offset-2 hover:underline">
            Abrir
          </Link>
        ) : (
          "Enviado"
        )}
      </span>
    );
  }
  return (
    <div className="flex shrink-0 items-center gap-1">
      {item.status === "failed" && (
        <Button type="button" variant="ghost" size="icon" onClick={onRetry} disabled={busy} aria-label={`Tentar enviar ${item.name} de novo`}>
          <RotateCcw className="h-4 w-4" />
        </Button>
      )}
      <Button type="button" variant="ghost" size="icon" onClick={onRemove} disabled={busy} aria-label={`Remover ${item.name}`}>
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
};
