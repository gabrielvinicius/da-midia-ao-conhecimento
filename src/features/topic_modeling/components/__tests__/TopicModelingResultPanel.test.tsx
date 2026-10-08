import { fireEvent, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { TopicModelingResultPanel } from "../TopicModelingResultPanel";
import { analysis, renderWithQuery } from "@/test/fixtures";

const renameTopic = vi.fn().mockResolvedValue(undefined);
vi.mock("@/features/summarization/api", () => ({
  renameTopic: (...args: unknown[]) => renameTopic(...args),
}));

describe("TopicModelingResultPanel", () => {
  it("lists the topics in the order they appear, with their time and share", () => {
    const onSeek = vi.fn();
    renderWithQuery(<TopicModelingResultPanel analysis={analysis()} onSeek={onSeek} />);
    const titles = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(titles).toEqual(["A origem do caos", "A era da IA"]); // sem o grupo de ruído
    expect(screen.getByText("75%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ir para 21:50" }));
    expect(onSeek).toHaveBeenCalledWith(1310);
  });

  it("renames a topic", async () => {
    renderWithQuery(<TopicModelingResultPanel analysis={analysis()} />);
    fireEvent.click(screen.getByRole("button", { name: /Corrigir o título do tema A era da IA/ }));
    fireEvent.change(screen.getByLabelText("Título do tema"), { target: { value: "IA generativa" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar título" }));
    await waitFor(() => expect(renameTopic).toHaveBeenCalledWith("a1", 1, "IA generativa"));
  });

  it("says the topics were not analysed when the step did not run", () => {
    // ANALYSIS_FACTORS sem "topics": as etapas registradas não incluem a de temas.
    renderWithQuery(
      <TopicModelingResultPanel analysis={analysis({ topics: [], diagnostics: { steps: { chunking: "ok" } } })} />,
    );
    expect(screen.getByText("Os temas não foram analisados nesta mídia.")).toBeInTheDocument();
  });

  it("says no topic was found when the step ran without finding any", () => {
    renderWithQuery(<TopicModelingResultPanel analysis={analysis({ topics: [] })} />);
    expect(screen.getByText("Nenhum tópico detectado.")).toBeInTheDocument();
  });
});
