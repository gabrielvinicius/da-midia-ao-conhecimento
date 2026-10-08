import { fireEvent, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { SummaryPanel } from "./SummaryPanel";
import { SUMMARY_APPENDIX, SUMMARY_BODY, analysis, renderWithQuery } from "@/test/fixtures";
import { MediaStatus } from "@/types";

const correctSummary = vi.fn().mockResolvedValue(undefined);
vi.mock("../api", () => ({
  correctSummary: (...args: unknown[]) => correctSummary(...args),
  submitAnalysisFeedback: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe("SummaryPanel", () => {
  it("shows the summary without the appendix and with the fidelity check", () => {
    renderWithQuery(<SummaryPanel analysis={analysis()} />);
    expect(screen.getByRole("heading", { name: "A crise da engenharia de software" })).toBeInTheDocument();
    expect(screen.queryByText(/Apêndice/)).not.toBeInTheDocument();
    expect(screen.queryByText("---")).not.toBeInTheDocument();
    expect(screen.getByText("As 3 frases verificadas têm apoio na transcrição.")).toBeInTheDocument();
  });

  it("edits with a preview and saves the body with the appendix the search uses", async () => {
    renderWithQuery(<SummaryPanel analysis={analysis()} />);
    fireEvent.click(screen.getByRole("button", { name: /Corrigir resumo/ }));

    const editor = screen.getByLabelText("Texto do resumo");
    expect(editor).toHaveValue(SUMMARY_BODY);
    fireEvent.change(editor, { target: { value: "# Novo título\n\nTexto revisado." } });
    expect(screen.getByLabelText("Pré-visualização")).toHaveTextContent("Novo título");
    fireEvent.click(screen.getByRole("button", { name: /Salvar correção/ }));

    await waitFor(() =>
      expect(correctSummary).toHaveBeenCalledWith("a1", "# Novo título\n\nTexto revisado." + SUMMARY_APPENDIX),
    );
  });

  it("compares a corrected summary with the AI version", () => {
    const corrected = analysis({
      summary: "# Revisado\n\nTexto do usuário." + SUMMARY_APPENDIX,
      diagnostics: { ...analysis().diagnostics, original_ai_summary: SUMMARY_BODY + SUMMARY_APPENDIX },
    });
    renderWithQuery(<SummaryPanel analysis={corrected} />);
    expect(screen.getByText("Resumo corrigido por você.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Ver versão da IA/ }));
    expect(screen.getByRole("heading", { name: "A crise da engenharia de software" })).toBeInTheDocument();
  });

  it("explains what happens before the analysis exists and hides editing from viewers", () => {
    renderWithQuery(<SummaryPanel analysis={null} mediaStatus={MediaStatus.ANALYZING} />);
    expect(screen.getByText("O resumo aparece aqui assim que a análise terminar.")).toBeInTheDocument();

    renderWithQuery(<SummaryPanel analysis={analysis()} canEdit={false} />);
    expect(screen.queryByRole("button", { name: /Corrigir resumo/ })).not.toBeInTheDocument();
  });
});
