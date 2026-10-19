import type { StudyDeckEntry } from "./api";

/** Resumo do progresso: o que já domina, o que está aprendendo e a taxa de acerto. */
export const progressSummary = (deck: StudyDeckEntry[]) => {
  const questions = deck.flatMap((e) => e.questions);
  const answered = questions.filter((q) => q.progress);
  const right = answered.reduce((n, q) => n + (q.progress?.correct_count ?? 0), 0);
  const wrong = answered.reduce((n, q) => n + (q.progress?.wrong_count ?? 0), 0);
  return {
    total: questions.length,
    mastered: answered.filter((q) => q.progress?.mastered).length,
    learning: answered.filter((q) => !q.progress?.mastered).length,
    fresh: questions.length - answered.length,
    due: questions.filter((q) => q.due).length,
    accuracy: right + wrong ? Math.round((right / (right + wrong)) * 100) : null,
  };
};
