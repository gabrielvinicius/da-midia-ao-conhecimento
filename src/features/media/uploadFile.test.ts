import { describe, expect, it } from "vitest";
import { MAX_FILE_SIZE, fileProblem, formatFileSize, uploadKind } from "./uploadFile";

describe("uploadKind", () => {
  it.each([
    ["aula.MP4", "video"],
    ["aula.flv", "video"],
    ["podcast.ogg", "audio"],
    ["notas.docx", "text"],
    ["quadro.jpeg", "text"],
    ["planilha.xlsx", null],
  ])("%s → %s", (name, kind) => {
    expect(uploadKind({ name })).toBe(kind);
  });
});

describe("fileProblem", () => {
  it("aceita um arquivo válido", () => {
    expect(fileProblem({ name: "aula.mp4", size: 10 })).toBeNull();
  });

  it("recusa ausente, grande demais ou de tipo não aceito", () => {
    expect(fileProblem(undefined)).toMatch(/obrigatório/);
    expect(fileProblem({ name: "aula.mp4", size: MAX_FILE_SIZE + 1 })).toMatch(/500 MB/);
    expect(fileProblem({ name: "planilha.xlsx", size: 10 })).toMatch(/Tipos aceitos/);
  });
});

describe("formatFileSize", () => {
  it("usa a maior unidade que cabe", () => {
    expect(formatFileSize(0)).toBe("0 Bytes");
    expect(formatFileSize(1536)).toBe("1.5 KB");
    expect(formatFileSize(5 * 1024 * 1024)).toBe("5 MB");
  });
});
