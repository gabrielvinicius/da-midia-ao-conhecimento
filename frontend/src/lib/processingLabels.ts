// Nomes das etapas do processamento, como o backend as registra.

const TASK_LABELS: Record<string, string> = {
  transcription: "Transcrição",
  visual_description: "Descrição dos quadros",
  text_analysis: "Análise completa",
  "analysis.chunking": "Divisão em trechos",
  "analysis.sentiment": "Sentimento",
  "analysis.topic_modeling": "Temas",
  "analysis.topic_titles": "Títulos dos temas",
  "analysis.knowledge_indexing": "Indexação semântica",
  // Execuções anteriores, quando a descrição dos quadros fazia parte da análise.
  "analysis.visual_insight": "Descrição dos quadros (análise)",
  "analysis.release_memory": "Liberação de memória da GPU",
  "analysis.content_genre": "Tipo de conteúdo",
  "analysis.synthesis": "Resumo final",
  "analysis.chapters": "Capítulos",
  "analysis.review_questions": "Perguntas de revisão",
  "analysis.grounding_check": "Verificação de fidelidade",
};

export const taskLabel = (task: string) => TASK_LABELS[task] ?? task;

export const formatSeconds = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return "—";
  if (value < 60) return `${value.toFixed(1)} s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes} min ${seconds} s`;
};
