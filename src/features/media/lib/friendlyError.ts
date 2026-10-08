// Motivo de uma falha em linguagem de quem usa o sistema. O texto técnico
// (ex.: "Library libcublas.so.12 is not found") fica nos detalhes.

const RULES: { pattern: RegExp; message: string }[] = [
  { pattern: /sem fala|no speech|nospeech/i, message: "Não encontramos fala nesta gravação." },
  {
    pattern: /cuda|cublas|cudnn|gpu|out of memory|memória/i,
    message: "O servidor não conseguiu usar a placa de vídeo para processar esta mídia.",
  },
  { pattern: /prazo|timeout|time limit|tempo/i, message: "O processamento demorou mais que o esperado e foi interrompido." },
  { pattern: /ollama|modelo de linguagem|language model/i, message: "O modelo de linguagem não respondeu." },
  { pattern: /format|codec|decod|corrupt|invalid data/i, message: "Não foi possível ler o arquivo. Ele pode estar corrompido ou num formato sem suporte." },
];

export const friendlyError = (message?: string | null): string => {
  const text = message ?? "";
  return RULES.find((rule) => rule.pattern.test(text))?.message ?? "O processamento desta mídia falhou.";
};
