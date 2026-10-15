import * as React from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { saveAs } from "file-saver";
import { ChevronDown, ChevronUp, Download, FileCode2, FileText, Printer, Search } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/DropdownMenu";
import { Card } from "@/components/ui/Card";
import ErrorState from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { Markdown } from "@/components/ui/Markdown";
import { Skeleton } from "@/components/ui/Skeleton";
import { splitSummary } from "@/features/media/lib/analysisContent";
import { useMediaNames } from "@/features/media/hooks/useMediaNames";
import { getNotebook, type NotebookEntry } from "@/features/summarization/api";
import { genreLabel } from "@/features/summarization/components/SummaryPanel";
import { normalizeText } from "@/lib/text";
import { buildNotebookPdf } from "@/features/summarization/notebookPdf";
import { toast } from "react-toastify";

const FILE_NAME = "caderno-de-resumos";

/** Um arquivo Markdown com todos os resumos, na ordem da tela. */
const notebookMarkdown = (entries: NotebookEntry[], nameOf: (id: string | null) => string) =>
  [
    "# Caderno de resumos",
    "",
    ...entries.flatMap((entry) => [
      `## ${nameOf(entry.media_id)}`,
      "",
      // Os títulos do resumo descem um nível para caberem sob o nome da mídia.
      splitSummary(entry.summary).body.replace(/^(#+)\s/gm, "$1## "),
      "",
    ]),
  ].join("\n");

const NotebookItem = ({ entry, name }: { entry: NotebookEntry; name: string }) => {
  const [open, setOpen] = React.useState(false);
  const body = splitSummary(entry.summary).body;
  const genre = genreLabel(entry.genre);
  return (
    <li className="rounded-xl border border-[#ede4d5] bg-white p-4 sm:p-6">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
        <Link to={entry.media_id ? `/media/${entry.media_id}` : "#"} className="font-semibold text-slate-900 wrap-anywhere hover:underline">
          {name}
        </Link>
        <p className="text-xs text-muted-foreground sm:whitespace-nowrap">
          {[genre, `${entry.chapters} capítulos`, `${entry.questions} perguntas`].filter(Boolean).join(" · ")}
        </p>
      </div>
      {entry.topics.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {entry.topics.map((topic) => (
            <span key={topic} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
              {topic}
            </span>
          ))}
        </div>
      )}
      <div className={open ? "mt-3" : "relative mt-3 max-h-48 overflow-hidden"}>
        <Markdown text={body} />
        {!open && <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-linear-to-t from-white " />}
      </div>
      <Button variant="ghost" size="sm" className="mt-2 -ml-2" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        {open ? <ChevronUp className="mr-2 h-4 w-4" /> : <ChevronDown className="mr-2 h-4 w-4" />}
        {open ? "Recolher" : "Ler tudo"}
      </Button>
    </li>
  );
};

/**
 * Caderno de resumos: os resumos de todas as mídias num lugar só, para ler,
 * buscar, baixar em Markdown ou imprimir (e salvar em PDF pelo navegador).
 */
const NotebookPage = () => {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["notebook"], queryFn: getNotebook });
  const nameOf = useMediaNames();
  const [search, setSearch] = React.useState("");

  const entries = React.useMemo(() => {
    const term = normalizeText(search.trim());
    return (data ?? []).filter(
      (e) => !term || normalizeText(`${nameOf(e.media_id)} ${e.topics.join(" ")} ${splitSummary(e.summary).body}`).includes(term),
    );
  }, [data, nameOf, search]);

  const [makingPdf, setMakingPdf] = React.useState(false);

  const downloadPdf = async () => {
    setMakingPdf(true);
    try {
      const blob = await buildNotebookPdf(
        "Caderno de resumos",
        entries.map((entry) => ({
          title: nameOf(entry.media_id),
          meta: [genreLabel(entry.genre), entry.topics.join(" · ")].filter(Boolean).join(" — "),
          markdown: splitSummary(entry.summary).body,
        })),
      );
      saveAs(blob, `${FILE_NAME}.pdf`);
    } catch (error) {
      console.error("Falha ao gerar o PDF", error);
      toast.error("Não foi possível gerar o PDF. Tente o Markdown ou Imprimir.");
    } finally {
      setMakingPdf(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Resumos</h1>
          <p className="text-sm text-muted-foreground">Os resumos de todas as suas mídias, para ler e estudar em sequência.</p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" disabled={entries.length === 0}>
                <Download className="mr-2 h-4 w-4" />
                Baixar
                <ChevronDown className="ml-2 h-3.5 w-3.5 opacity-60" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64">
              <DropdownMenuItem onSelect={downloadPdf} disabled={makingPdf} className="items-start gap-3 py-2">
                <FileText className="mt-0.5 h-4 w-4 text-slate-500" />
                <span className="flex flex-col">
                  <span className="text-sm text-slate-900">{makingPdf ? "Gerando PDF..." : "PDF"}</span>
                  <span className="text-xs text-slate-500">Para ler, imprimir ou enviar</span>
                </span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={() =>
                  saveAs(new Blob([notebookMarkdown(entries, nameOf)], { type: "text/markdown;charset=utf-8" }), `${FILE_NAME}.md`)
                }
                className="items-start gap-3 py-2"
              >
                <FileCode2 className="mt-0.5 h-4 w-4 text-slate-500" />
                <span className="flex flex-col">
                  <span className="text-sm text-slate-900">Markdown (.md)</span>
                  <span className="text-xs text-slate-500">Para editar ou levar a outro aplicativo</span>
                </span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="outline" disabled={entries.length === 0} onClick={() => window.print()}>
            <Printer className="mr-2 h-4 w-4" />
            Imprimir
          </Button>
        </div>
      </div>

      <div className="relative max-w-md ">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar nos resumos" aria-label="Buscar nos resumos" className="pl-9" />
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState title="Não foi possível carregar os resumos" message="Tente novamente em instantes." onRetry={() => refetch()} />
      ) : (data ?? []).length === 0 ? (
        <Card className="border-[#ede4d5] p-8 text-center">
          <p className="font-medium text-slate-900">Nenhum resumo ainda</p>
          <p className="mt-1 text-sm text-muted-foreground">Os resumos aparecem aqui quando a análise de cada mídia termina.</p>
        </Card>
      ) : entries.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Nenhum resumo menciona “{search}”.</p>
      ) : (
        <ul className="space-y-4">
          {entries.map((entry) => (
            <NotebookItem key={entry.analysis_id} entry={entry} name={nameOf(entry.media_id)} />
          ))}
        </ul>
      )}
      {/* Na impressão só este bloco aparece (index.css): os resumos inteiros, sem menu. */}
      {createPortal(
        <div className="print-only">
          <h1>Caderno de resumos</h1>
          {entries.map((entry) => (
            <section key={entry.analysis_id}>
              <h2>{nameOf(entry.media_id)}</h2>
              <Markdown text={splitSummary(entry.summary).body} />
            </section>
          ))}
        </div>,
        document.body,
      )}
    </div>
  );
};

export default NotebookPage;
