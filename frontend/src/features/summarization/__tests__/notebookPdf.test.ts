import { describe, expect, it } from "vitest";

import { buildNotebookPdf, markdownBlocks, plainInline } from "../notebookPdf";

describe("PDF do caderno de resumos", () => {
  it("tira a marcação de ênfase, código e links", () => {
    expect(plainInline("A **LGPD** e o `art. 7º` ([lei](https://x.y)) _valem_")).toBe("A LGPD e o art. 7º (lei) valem");
  });

  it("separa títulos, parágrafos e listas", () => {
    const blocks = markdownBlocks("# Aula\n\nPrimeira linha\ncontinua.\n\n## Pontos\n- um\n- **dois**\n1. passo\n\n---\nFim");
    expect(blocks).toEqual([
      { kind: "h1", text: "Aula" },
      { kind: "p", text: "Primeira linha continua." },
      { kind: "h2", text: "Pontos" },
      { kind: "li", text: "um", marker: "•" },
      { kind: "li", text: "dois", marker: "•" },
      { kind: "li", text: "passo", marker: "1." },
      { kind: "p", text: "Fim" },
    ]);
  });

  it("gera um PDF com várias páginas quando o texto é longo", async () => {
    const long = Array.from({ length: 120 }, (_, i) => `Parágrafo ${i} sobre proteção de dados e concessão.`).join("\n\n");
    const blob = await buildNotebookPdf("Caderno de resumos", [
      { title: "aula1.mp4", meta: "Aula — Proteção de dados", markdown: `# Aula\n\n${long}` },
    ]);
    const content = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.readAsText(blob);
    });
    expect(content.startsWith("%PDF-")).toBe(true);
    expect((content.match(/\/Type \/Page\b/g) ?? []).length).toBeGreaterThan(1);
  });
});
