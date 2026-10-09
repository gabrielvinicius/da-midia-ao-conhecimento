import type { StudyDeckEntry } from "./api";

/** A partir desta caixa (de 1 a 5) a pergunta conta como dominada; igual ao backend. */
export const MASTERED_BOX = 4;

/** Resumo do progresso: o que já domina, o que está aprendendo e a taxa de acerto. */
export const progressSummary = (deck: StudyDeckEntry[]) => {
  const questions = deck.flatMap((e) => e.questions);
  const answered = questions.filter((q) => q.progress);
  const right = answered.reduce((n, q) => n + (q.progress?.correct_count ?? 0), 0);
  const wrong = answered.reduce((n, q) => n + (q.progress?.wrong_count ?? 0), 0);
  return {
    total: questions.length,
    mastered: answered.filter((q) => (q.progress?.box ?? 0) >= MASTERED_BOX).length,
    learning: answered.filter((q) => (q.progress?.box ?? 0) < MASTERED_BOX).length,
    fresh: questions.length - answered.length,
    due: questions.filter((q) => q.due).length,
    accuracy: right + wrong ? Math.round((right / (right + wrong)) * 100) : null,
  };
};
