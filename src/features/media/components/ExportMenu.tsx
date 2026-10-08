import { saveAs } from "file-saver";
import { Braces, Captions, ChevronDown, Download, FileText, GraduationCap, Printer, ScrollText } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import {
  baseFileName,
  everythingJson,
  studyGuideMarkdown,
  summaryMarkdown,
  transcriptSrt,
  transcriptText,
  transcriptVtt,
  type ExportInput,
} from "../lib/exporters";
import { splitSummary } from "../lib/analysisContent";

type Option = {
  label: string;
  hint: string;
  icon: ReactNode;
  suffix: string;
  type: string;
  build: (input: ExportInput) => string;
  available: boolean;
};

const download = (content: string, name: string, type: string) =>
  saveAs(new Blob([content], { type: `${type};charset=utf-8` }), name);

/**
 * Tudo o que a análise extraiu, para baixar: resumo, guia de estudo,
 * transcrição (texto ou legendas) e os dados completos. Os arquivos são
 * montados no navegador, com o que a página já carregou.
 */
export const ExportMenu = ({ input, onPrint }: { input: ExportInput; onPrint?: () => void }) => {
  const hasSummary = Boolean(splitSummary(input.analysis?.summary).body);
  const hasTranscript = Boolean(input.transcription?.text?.trim());
  const timed = (input.transcription?.segments ?? []).some((s) => s.end > 0);
  const base = baseFileName(input.media);

  const groups: { title: string; options: Option[] }[] = [
    {
      title: "Resumo e estudo",
      options: [
        {
          label: "Resumo",
          hint: "Markdown (.md)",
          icon: <FileText className="h-4 w-4" />,
          suffix: "-resumo.md",
          type: "text/markdown",
          build: summaryMarkdown,
          available: hasSummary,
        },
        {
          label: "Guia de estudo completo",
          hint: "Resumo, capítulos, perguntas, temas (.md)",
          icon: <GraduationCap className="h-4 w-4" />,
          suffix: "-guia-de-estudo.md",
          type: "text/markdown",
          build: studyGuideMarkdown,
          available: hasSummary,
        },
      ],
    },
    {
      title: "Transcrição",
      options: [
        {
          label: "Texto com horários",
          hint: "Texto (.txt)",
          icon: <ScrollText className="h-4 w-4" />,
          suffix: "-transcricao.txt",
          type: "text/plain",
          build: transcriptText,
          available: hasTranscript,
        },
        {
          label: "Legendas SRT",
          hint: "Para reprodutores e editores de vídeo",
          icon: <Captions className="h-4 w-4" />,
          suffix: ".srt",
          type: "application/x-subrip",
          build: transcriptSrt,
          available: hasTranscript && timed,
        },
        {
          label: "Legendas WebVTT",
          hint: "Para páginas web (.vtt)",
          icon: <Captions className="h-4 w-4" />,
          suffix: ".vtt",
          type: "text/vtt",
          build: transcriptVtt,
          available: hasTranscript && timed,
        },
      ],
    },
    {
      title: "Dados",
      options: [
        {
          label: "Tudo em JSON",
          hint: "Para outras ferramentas",
          icon: <Braces className="h-4 w-4" />,
          suffix: "-dados.json",
          type: "application/json",
          build: everythingJson,
          available: hasSummary || hasTranscript,
        },
      ],
    },
  ];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Download className="h-4 w-4" /> Baixar <ChevronDown className="h-3.5 w-3.5 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        {groups.map((group, g) => (
          <div key={group.title}>
            {g > 0 && <DropdownMenuSeparator />}
            <DropdownMenuLabel className="text-xs font-medium text-slate-500">{group.title}</DropdownMenuLabel>
            {group.options.map((option) => (
              <DropdownMenuItem
                key={option.label}
                disabled={!option.available}
                onSelect={() => download(option.build(input), base + option.suffix, option.type)}
                className="items-start gap-3 py-2"
              >
                <span className="mt-0.5 text-slate-500">{option.icon}</span>
                <span className="flex flex-col">
                  <span className="text-sm text-slate-900">{option.label}</span>
                  <span className="text-xs text-slate-500">{option.hint}</span>
                </span>
              </DropdownMenuItem>
            ))}
          </div>
        ))}
        {onPrint && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={onPrint} disabled={!hasSummary} className="items-start gap-3 py-2">
              <span className="mt-0.5 text-slate-500"><Printer className="h-4 w-4" /></span>
              <span className="flex flex-col">
                <span className="text-sm text-slate-900">Imprimir ou salvar em PDF</span>
                <span className="text-xs text-slate-500">Resumo e guia de estudo</span>
              </span>
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
