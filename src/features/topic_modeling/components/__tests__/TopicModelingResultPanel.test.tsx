import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { TopicModelingResultPanel } from "../TopicModelingResultPanel";

let analysis: Record<string, unknown> = {};

vi.mock("@/features/summarization/hooks/useAnalysisQuery", () => ({
  useTextAnalysisByMediaIdQuery: () => ({ data: analysis, isLoading: false, isError: false }),
}));

describe("TopicModelingResultPanel", () => {
  it("says the topics were not analysed when the step did not run", () => {
    // ANALYSIS_FACTORS sem "topics": as etapas registradas não incluem a de temas.
    analysis = { topics: [], diagnostics: { steps: { chunking: "ok", synthesis: "ok" } } };
    render(<TopicModelingResultPanel mediaId="m1" />);
    expect(screen.getByText("Os temas não foram analisados nesta mídia.")).toBeInTheDocument();
  });

  it("says no topic was found when the step ran without finding any", () => {
    analysis = { topics: [], diagnostics: { steps: { topic_modeling: "ok" } } };
    render(<TopicModelingResultPanel mediaId="m1" />);
    expect(screen.getByText("Nenhum tópico detectado.")).toBeInTheDocument();
  });
});
