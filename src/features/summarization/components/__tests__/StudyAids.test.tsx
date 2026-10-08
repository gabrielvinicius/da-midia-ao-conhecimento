import { fireEvent, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { StudyAids } from "@/features/summarization/components/StudyAids";
import { ChapterNav } from "@/features/summarization/components/ChapterNav";
import { analysis, renderWithQuery } from "@/test/fixtures";

const correctStudyAids = vi.fn().mockResolvedValue(undefined);
vi.mock("@/features/summarization/api", () => ({
  correctStudyAids: (...args: unknown[]) => correctStudyAids(...args),
}));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe("StudyAids", () => {
  it("hides answers until asked and takes the player to the answer", () => {
    const onSeek = vi.fn();
    renderWithQuery(<StudyAids analysis={analysis()} onSeek={onSeek} />);

    expect(screen.queryByText("17 desenvolvedores.")).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByText("Mostrar resposta")[0]);
    expect(screen.getByText("17 desenvolvedores.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ir para 12:20" }));
    expect(onSeek).toHaveBeenCalledWith(740);
  });

  it("quizzes one question at a time", () => {
    renderWithQuery(<StudyAids analysis={analysis()} />);
    fireEvent.click(screen.getByRole("button", { name: /Testar-me/ }));
    expect(screen.getByText("Pergunta 1 de 2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Revelar resposta" }));
    expect(screen.getByText(/17 desenvolvedores\./)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próxima pergunta" }));
    expect(screen.getByText("Pergunta 2 de 2")).toBeInTheDocument();
  });

  it("saves edited chapter titles and questions, keeping the chapter times", async () => {
    renderWithQuery(<StudyAids analysis={analysis()} />);
    fireEvent.click(screen.getByRole("button", { name: /Editar capítulos e perguntas/ }));

    fireEvent.change(screen.getByLabelText("Título do capítulo 2"), { target: { value: "Manifesto ágil (2001)" } });
    fireEvent.click(screen.getByRole("button", { name: "Remover pergunta 2" }));
    fireEvent.change(screen.getByLabelText("Momento da resposta 1"), { target: { value: "12:30" } });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/ }));

    await waitFor(() => expect(correctStudyAids).toHaveBeenCalled());
    const [analysisId, payload] = correctStudyAids.mock.calls[0];
    expect(analysisId).toBe("a1");
    expect(payload.chapters[1]).toEqual({ start: 600, end: 1310, title: "Manifesto ágil (2001)" });
    expect(payload.review_questions).toEqual([
      { question: "Quantos autores teve o manifesto ágil?", answer: "17 desenvolvedores.", start: 750 },
    ]);
  });

  it("explains when there is nothing to study", () => {
    renderWithQuery(<StudyAids analysis={analysis({ diagnostics: {} })} />);
    expect(screen.getByText(/não tem capítulos nem perguntas/)).toBeInTheDocument();
  });
});

describe("ChapterNav", () => {
  it("highlights the chapter being played and moves the player", () => {
    const onSeek = vi.fn();
    const chapters = analysis().diagnostics.chapters as { start: number; end: number; title: string }[];
    renderWithQuery(<ChapterNav chapters={chapters} currentTime={700} duration={1780} onSeek={onSeek} />);

    expect(screen.getByRole("button", { name: /O manifesto ágil/ })).toHaveAttribute("aria-current", "true");
    fireEvent.click(screen.getByRole("button", { name: /A era da IA generativa/ }));
    expect(onSeek).toHaveBeenCalledWith(1310);
  });
});
