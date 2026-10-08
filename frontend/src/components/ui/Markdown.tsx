import { Fragment, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Markdown do resumo: títulos, parágrafos, listas, citações, linha
 * horizontal, **negrito** e _itálico_. Sem HTML do texto (nada é injetado):
 * cada bloco vira um elemento React. Antes, "---", ">" e "_..._" apareciam
 * crus na página.
 */
export const Markdown = ({ text, className }: { text: string; className?: string }) => (
  <div className={cn("space-y-3 text-[15px] leading-7 text-slate-800", className)}>
    {blocks(text).map((block, i) => (
      <Fragment key={i}>{renderBlock(block)}</Fragment>
    ))}
  </div>
);

type Block =
  | { kind: "h1" | "h2" | "h3" | "p" | "quote"; text: string }
  | { kind: "ul" | "ol"; items: string[] }
  | { kind: "hr" };

const LIST_ITEM = /^\s*[-*+]\s+/;
const ORDERED_ITEM = /^\s*\d+[.)]\s+/;

const blocks = (text: string): Block[] => {
  const result: Block[] = [];
  let paragraph: string[] = [];
  const flush = () => {
    if (paragraph.length) result.push({ kind: "p", text: paragraph.join(" ") });
    paragraph = [];
  };
  for (const raw of (text || "").split("\n")) {
    const line = raw.trim();
    const last = result[result.length - 1];
    if (!line) {
      flush();
    } else if (/^(-{3,}|\*{3,}|_{3,})$/.test(line)) {
      flush();
      result.push({ kind: "hr" });
    } else if (/^#{1,6}\s/.test(line)) {
      flush();
      const level = line.match(/^#+/)![0].length;
      result.push({ kind: level === 1 ? "h1" : level === 2 ? "h2" : "h3", text: line.replace(/^#+\s+/, "") });
    } else if (line.startsWith(">")) {
      flush();
      const content = line.replace(/^>\s?/, "");
      if (last?.kind === "quote") last.text += content ? ` ${content}` : "";
      else if (content) result.push({ kind: "quote", text: content });
    } else if (LIST_ITEM.test(line) || ORDERED_ITEM.test(line)) {
      flush();
      const kind = LIST_ITEM.test(line) ? "ul" : "ol";
      const item = line.replace(kind === "ul" ? LIST_ITEM : ORDERED_ITEM, "");
      if (last?.kind === kind) last.items.push(item);
      else result.push({ kind, items: [item] });
    } else {
      paragraph.push(line);
    }
  }
  flush();
  return result;
};

const renderBlock = (block: Block): ReactNode => {
  switch (block.kind) {
    case "h1":
      return <h2 className="pt-1 text-2xl font-semibold leading-snug tracking-tight text-slate-950">{inline(block.text)}</h2>;
    case "h2":
      return <h3 className="pt-4 text-lg font-semibold text-slate-900">{inline(block.text)}</h3>;
    case "h3":
      return <h4 className="pt-3 text-base font-semibold text-slate-900">{inline(block.text)}</h4>;
    case "quote":
      return (
        <blockquote className="border-l-2 border-amber-400 bg-amber-50/60 py-2 pl-4 pr-3 text-slate-700">
          {inline(block.text)}
        </blockquote>
      );
    case "ul":
    case "ol": {
      const List = block.kind === "ul" ? "ul" : "ol";
      return (
        <List className={cn("space-y-1.5 pl-5", block.kind === "ul" ? "list-disc marker:text-amber-500" : "list-decimal")}>
          {block.items.map((item, i) => (
            <li key={i} className="pl-1">{inline(item)}</li>
          ))}
        </List>
      );
    }
    case "hr":
      return <hr className="my-2 border-slate-200" />;
    default:
      return <p>{inline(block.text)}</p>;
  }
};

/** **negrito**, *itálico* e _itálico_ dentro de uma linha. */
const inline = (text: string): ReactNode[] =>
  text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|_[^_\s][^_]*_)/g).map((part, i) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={i} className="font-semibold text-slate-950">{part.slice(2, -2)}</strong>;
    if (/^(\*[^*]+\*|_[^_]+_)$/.test(part)) return <em key={i}>{part.slice(1, -1)}</em>;
    return part;
  });
