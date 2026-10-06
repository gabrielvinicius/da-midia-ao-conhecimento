import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { SentimentResultPanel } from "../SentimentResultPanel";

const analysisWithTone = {
  overall_sentiment: "positive", // o backend devolve o rótulo em minúsculas
  sentiment_items: [
    { chunk_id: "1", label: "positive", score: 0.9, text: "Ótima aula." },
    { chunk_id: "2", label: "neutral", score: 0.7, text: "Vamos ao exemplo." },
  ],
};
let analysis: Record<string, unknown> = analysisWithTone;

vi.mock("@/features/summarization/hooks/useAnalysisQuery", () => ({
  useTextAnalysisByMediaIdQuery: () => ({ data: analysis, isLoading: false, isError: false }),
}));

describe("SentimentResultPanel", () => {
  beforeEach(() => {
    analysis = analysisWithTone;
  });

  it("shows the overall tone returned by the backend", () => {
    render(<SentimentResultPanel mediaId="m1" />);
    // tom geral e rótulo da amostra de trechos, ambos em português
    expect(screen.getAllByText("Positivo").length).toBeGreaterThan(1);
    expect(screen.queryByText("POSITIVE")).not.toBeInTheDocument();
    expect(screen.getByText(/Baseado em 2 blocos/i)).toBeInTheDocument();
  });

  it("does not call an unanalysed tone neutral", () => {
    // ANALYSIS_FACTORS sem "sentiment": a análise chega sem tom.
    analysis = { overall_sentiment: null, sentiment_items: [] };
    render(<SentimentResultPanel mediaId="m1" />);
    expect(screen.getByText("O tom não foi analisado nesta mídia.")).toBeInTheDocument();
    expect(screen.queryByText("Neutro")).not.toBeInTheDocument();
  });
});
