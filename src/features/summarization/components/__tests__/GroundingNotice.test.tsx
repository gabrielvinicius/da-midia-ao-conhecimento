import { fireEvent, render, screen } from "@testing-library/react";
import { GroundingNotice } from "@/features/summarization/components/GroundingNotice";
import { summarySourceLabel } from "@/features/summarization/components/SummaryPanel";

describe("GroundingNotice", () => {
  it("lists the sentences without support, with the closest moment", () => {
    render(
      <GroundingNotice
        report={{
          checked: 10,
          supported: 9,
          ratio: 0.9,
          threshold: 0.8,
          unsupported: [{ text: "O professor citou um estudo de 2019.", best_score: 0.71, closest_start: 754 }],
        }}
      />
    );
    expect(screen.getByText(/9 de 10 frases têm apoio na transcrição/)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Frases sem trecho parecido/));
    expect(screen.getByText(/estudo de 2019/)).toBeInTheDocument();
    expect(screen.getByText(/trecho mais próximo em 12:34/)).toBeInTheDocument();
  });

  it("says when every sentence is supported and hides without a report", () => {
    const { rerender, container } = render(
      <GroundingNotice report={{ checked: 7, supported: 7, ratio: 1, threshold: 0.8, unsupported: [] }} />
    );
    expect(screen.getByText(/As 7 frases verificadas têm apoio/)).toBeInTheDocument();
    rerender(<GroundingNotice report={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("summarySourceLabel", () => {
  it("labels each origin of the summary correctly", () => {
    expect(summarySourceLabel("llm")).toBe("Gerado pelo modelo principal");
    expect(summarySourceLabel("reserve")).toBe("Gerado pelo modelo reserva");
    // análises antigas: "fallback" significava que os dois modelos falharam
    expect(summarySourceLabel("fallback")).toMatch(/Resumo simplificado/);
    expect(summarySourceLabel("simplified")).toMatch(/Resumo simplificado/);
  });
});
