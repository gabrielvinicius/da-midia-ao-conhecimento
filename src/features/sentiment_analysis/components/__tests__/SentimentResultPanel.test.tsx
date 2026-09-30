import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { SentimentResultPanel } from "../SentimentResultPanel";

vi.mock("@/hooks/useQueries", () => ({
  useTextAnalysisByMediaIdQuery: () => ({
    data: {
      overall_sentiment: "positive", // o backend devolve o rótulo em minúsculas
      sentiment_items: [
        { chunk_id: "1", label: "positive", score: 0.9, text: "Ótima aula." },
        { chunk_id: "2", label: "neutral", score: 0.7, text: "Vamos ao exemplo." },
      ],
    },
    isLoading: false,
    isError: false,
  }),
}));

describe("SentimentResultPanel", () => {
  it("shows the overall tone returned by the backend", () => {
    render(<SentimentResultPanel mediaId="m1" />);
    expect(screen.getByText("Positivo")).toBeInTheDocument();
    expect(screen.getByText(/Baseado em 2 blocos/i)).toBeInTheDocument();
  });
});
