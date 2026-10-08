import { analysis, media, transcription } from "@/test/fixtures";
import {
  baseFileName,
  everythingJson,
  studyGuideMarkdown,
  summaryMarkdown,
  transcriptSrt,
  transcriptText,
  transcriptVtt,
} from "./exporters";
import { activeChapterIndex, screenMomentsOf, splitSummary, summaryTitle, toneCounts, topicsInOrder } from "./analysisContent";
import { friendlyError } from "./friendlyError";

const input = { media: media(), analysis: analysis(), transcription: transcription() };

describe("conteúdo da análise", () => {
  it("separa o resumo do apêndice e acha o título", () => {
    const { body, appendix } = splitSummary(input.analysis.summary);
    expect(body).not.toContain("Apêndice");
    expect(appendix.startsWith("\n\n---\n# Apêndice")).toBe(true);
    expect(summaryTitle(input.analysis.summary)).toBe("A crise da engenharia de software");
    expect(splitSummary("só o resumo")).toEqual({ body: "só o resumo", appendix: "" });
  });

  it("lê o que aparecia na tela, os temas em ordem e o tom", () => {
    expect(screenMomentsOf(input.analysis)).toEqual([
      { start: 332, text: 'Um slide com o texto "Clean Code".' },
      { start: null, text: "sem horário" },
    ]);
    expect(topicsInOrder(input.analysis).map((t) => t.title)).toEqual(["A origem do caos", "A era da IA"]);
    expect(toneCounts(input.analysis)).toEqual({ positive: 1, neutral: 1, negative: 2, total: 4 });
  });

  it("acha o capítulo em reprodução", () => {
    const chapters = [{ start: 0, end: 10, title: "a" }, { start: 10, end: 20, title: "b" }];
    expect(activeChapterIndex(chapters, 12)).toBe(1);
    expect(activeChapterIndex(chapters, 0)).toBe(0);
    expect(activeChapterIndex([], 5)).toBe(-1);
  });
});

describe("arquivos para baixar", () => {
  it("nomeia os arquivos pelo nome da mídia, sem acentos", () => {
    expect(baseFileName(media())).toBe("a-historia-nao-contada");
    expect(baseFileName(media({ filename: null }))).toBe("m1");
  });

  it("baixa o resumo sem o apêndice", () => {
    const text = summaryMarkdown(input);
    expect(text).toContain("# A crise da engenharia de software");
    expect(text).not.toContain("Apêndice");
  });

  it("monta o guia de estudo com capítulos, perguntas, respostas, temas e tom", () => {
    const guide = studyGuideMarkdown(input);
    expect(guide).toContain("- [10:00] O manifesto ágil");
    expect(guide).toContain("1. Quantos autores teve o manifesto ágil?\n   - Resposta: 17 desenvolvedores. (12:20)");
    expect(guide).toContain("- [00:00] **A origem do caos** — década, crise");
    expect(guide).toContain("2 trechos negativos, 1 neutros e 1 positivos (de 4).");
    expect(guide).toContain("Duração: 29:40");
    expect(guide).not.toContain("Apêndice");
  });

  it("baixa a transcrição em texto com horários e em legendas SRT e WebVTT", () => {
    expect(transcriptText(input)).toBe("[00:00] Estamos diante de uma crise.\n[00:03] Vamos falar de clin code.\n");
    expect(transcriptSrt(input)).toBe(
      "1\n00:00:00,000 --> 00:00:03,500\nEstamos diante de uma crise.\n\n2\n00:00:03,500 --> 00:00:07,250\nVamos falar de clin code.\n",
    );
    expect(transcriptVtt(input).startsWith("WEBVTT\n\n00:00:00.000 --> 00:00:03.500\nEstamos diante")).toBe(true);
  });

  it("documentos sem horários saem como texto corrido", () => {
    const doc = { ...input, transcription: transcription({ segments: [], text: "Art. 1º Esta Lei dispõe..." }) };
    expect(transcriptText(doc)).toBe("Art. 1º Esta Lei dispõe...\n");
    expect(transcriptSrt(doc)).toBe("");
  });

  it("reúne tudo em JSON", () => {
    const data = JSON.parse(everythingJson(input));
    expect(data.summary).not.toContain("Apêndice");
    expect(data.chapters).toHaveLength(3);
    expect(data.transcript.segments[1]).toEqual({ start: 3.5, end: 7.25, text: " Vamos falar de clin code." });
    expect(data.media.duration).toBe(1780);
  });
});

describe("friendlyError", () => {
  it("troca o erro técnico por um motivo compreensível", () => {
    expect(friendlyError("Library libcublas.so.12 is not found")).toBe(
      "O servidor não conseguiu usar a placa de vídeo para processar esta mídia.",
    );
    expect(friendlyError("NoSpeechFoundError: sem fala")).toBe("Não encontramos fala nesta gravação.");
    expect(friendlyError(null)).toBe("O processamento desta mídia falhou.");
  });
});
