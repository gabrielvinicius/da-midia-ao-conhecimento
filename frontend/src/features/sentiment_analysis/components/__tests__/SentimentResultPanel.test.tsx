import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { SentimentResultPanel } from "../SentimentResultPanel";
import { analysis } from "@/test/fixtures";

describe("SentimentResultPanel", () => {
  it("shows the real distribution of the tone, not only the predominant label", () => {
    render(<SentimentResultPanel analysis={analysis()} />);
    expect(screen.getByText("Negativo", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "2 negativo, 1 neutro, 1 positivo" })).toBeInTheDocument();
    expect(screen.queryByText("NEGATIVE")).not.toBeInTheDocument();
  });

  it("moves the player to a part of the recording from the tone timeline", () => {
    const onSeek = vi.fn();
    render(<SentimentResultPanel analysis={analysis()} onSeek={onSeek} compact />);
    fireEvent.click(screen.getByRole("button", { name: "Positivo em 03:00" }));
    expect(onSeek).toHaveBeenCalledWith(180);
  });

  it("does not call an unanalysed tone neutral", () => {
    render(<SentimentResultPanel analysis={analysis({ sentiment_items: [], overall_sentiment: "" })} />);
    expect(screen.getByText("O tom não foi analisado nesta mídia.")).toBeInTheDocument();
  });
});
