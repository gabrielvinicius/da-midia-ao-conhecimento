// PDF do caderno de resumos, desenhado como texto com o jsPDF (sem captura de
// tela: o texto continua selecionável e pesquisável no arquivo).
import type { jsPDF as JsPdf } from "jspdf";

export type PdfSection = { title: string; meta?: string; markdown: string };

const PAGE = { margin: 18, width: 210, height: 297 }; // A4, em mm
const LINE = 1.45; // altura da linha em relação ao tamanho da fonte
const MM_PER_PT = 0.3528;

type Block = { kind: "h1" | "h2" | "h3" | "p" | "li"; text: string; marker?: string };

/** Tira a marcação de ênfase, código e links: o PDF usa só as fontes padrão. */
export const plainInline = (text: string) =>
  text
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/(^|\W)[*_](\S.*?\S|\S)[*_](?=\W|$)/g, "$1$2")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");

/** Markdown simples (títulos, parágrafos, listas) em blocos para desenhar. */
export const markdownBlocks = (markdown: string): Block[] => {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  const flush = () => {
    if (paragraph.length) blocks.push({ kind: "p", text: plainInline(paragraph.join(" ")) });
    paragraph = [];
  };
  for (const raw of markdown.split("\n")) {
    const line = raw.trim();
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    const bullet = /^[-*+]\s+(.*)$/.exec(line);
    const numbered = /^(\d+)[.)]\s+(.*)$/.exec(line);
    if (!line || /^-{3,}$/.test(line)) flush();
    else if (heading) {
      flush();
      const level = Math.min(heading[1].length, 3);
      blocks.push({ kind: (["h1", "h2", "h3"] as const)[level - 1], text: plainInline(heading[2]) });
    } else if (bullet || numbered) {
      flush();
      blocks.push({ kind: "li", text: plainInline((bullet ?? numbered)![bullet ? 1 : 2]), marker: bullet ? "•" : `${numbered![1]}.` });
    } else paragraph.push(line);
  }
  flush();
  return blocks;
};

const STYLE: Record<Block["kind"], { size: number; bold: boolean; before: number }> = {
  h1: { size: 15, bold: true, before: 5 },
  h2: { size: 12.5, bold: true, before: 4 },
  h3: { size: 11, bold: true, before: 3 },
  p: { size: 10.5, bold: false, before: 2 },
  li: { size: 10.5, bold: false, before: 1 },
};

class Writer {
  y = PAGE.margin;

  constructor(private readonly doc: JsPdf) {}

  private lineHeight(size: number) {
    return size * MM_PER_PT * LINE;
  }

  private ensure(height: number) {
    if (this.y + height > PAGE.height - PAGE.margin) {
      this.doc.addPage();
      this.y = PAGE.margin;
    }
  }

  text(text: string, size: number, bold: boolean, options: { before?: number; indent?: number; marker?: string; gray?: boolean } = {}) {
    const { before = 0, indent = 0, marker, gray } = options;
    const doc = this.doc;
    doc.setFont("helvetica", bold ? "bold" : "normal");
    doc.setFontSize(size);
    doc.setTextColor(gray ? 110 : 20);
    const width = PAGE.width - 2 * PAGE.margin - indent;
    const lines = doc.splitTextToSize(text, width) as string[];
    const height = this.lineHeight(size);
    this.y += before;
    // Um título nunca fica sozinho no pé da página.
    this.ensure(height * Math.min(lines.length, bold ? 3 : 1));
    lines.forEach((line, index) => {
      this.ensure(height);
      if (marker && index === 0) doc.text(marker, PAGE.margin + indent - 4, this.y + height * 0.75);
      doc.text(line, PAGE.margin + indent, this.y + height * 0.75);
      this.y += height;
    });
  }

  rule() {
    this.y += 3;
    this.ensure(4);
    this.doc.setDrawColor(220);
    this.doc.line(PAGE.margin, this.y, PAGE.width - PAGE.margin, this.y);
    this.y += 3;
  }
}

/** Monta o PDF: capa simples, uma seção por mídia e o número das páginas. */
export const buildNotebookPdf = async (title: string, sections: PdfSection[]): Promise<Blob> => {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  doc.setProperties({ title });
  const writer = new Writer(doc);

  writer.text(title, 20, true);
  writer.text(`${sections.length} ${sections.length === 1 ? "mídia" : "mídias"} · ${new Date().toLocaleDateString("pt-BR")}`, 10, false, {
    before: 1,
    gray: true,
  });

  sections.forEach((section) => {
    writer.rule();
    writer.text(section.title, 16, true, { before: 2 });
    if (section.meta) writer.text(section.meta, 9.5, false, { before: 1, gray: true });
    for (const block of markdownBlocks(section.markdown)) {
      const style = STYLE[block.kind];
      writer.text(block.text, style.size, style.bold, {
        before: style.before,
        indent: block.kind === "li" ? 5 : 0,
        marker: block.marker,
      });
    }
  });

  const pages = doc.getNumberOfPages();
  for (let page = 1; page <= pages; page++) {
    doc.setPage(page);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.5);
    doc.setTextColor(140);
    doc.text(`${page} de ${pages}`, PAGE.width - PAGE.margin, PAGE.height - 8, { align: "right" });
  }
  return doc.output("blob");
};
