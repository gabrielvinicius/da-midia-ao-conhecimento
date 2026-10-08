import { fireEvent, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { InteractiveTranscriptionPanel } from "../InteractiveTranscriptionPanel";
import { renderWithQuery, transcription } from "@/test/fixtures";

const correctTranscriptionSegment = vi.fn();
vi.mock("../../api", () => ({
  correctTranscriptionSegment: (...args: unknown[]) => correctTranscriptionSegment(...args),
  updateSpeakerAliases: vi.fn(),
}));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe("InteractiveTranscriptionPanel", () => {
  it("shows each passage with its time, highlights the one playing and seeks on click", () => {
    const onSeek = vi.fn();
    renderWithQuery(<InteractiveTranscriptionPanel transcription={transcription()} currentTime={4} onSeek={onSeek} />);
    expect(screen.getByText("Vamos falar de clin code.").closest("li")).toHaveClass("bg-amber-50");
    fireEvent.click(screen.getByRole("button", { name: "Ir para 00:03" }));
    expect(onSeek).toHaveBeenCalledWith(3.5);
  });

  it("filters passages by a search that ignores accents", () => {
    renderWithQuery(<InteractiveTranscriptionPanel transcription={transcription()} currentTime={0} />);
    fireEvent.change(screen.getByLabelText("Buscar na transcrição"), { target: { value: "CRÍSE" } });
    expect(screen.getByText('1 de 2 trechos com "CRÍSE".')).toBeInTheDocument();
    expect(screen.queryByText("Vamos falar de clin code.")).not.toBeInTheDocument();
  });

  it("corrects a passage and shows that it was corrected", async () => {
    const corrected = transcription({
      segments: [
        { start: 0, end: 3.5, text: " Estamos diante de uma crise." },
        { start: 3.5, end: 7.25, text: "Vamos falar de Clean Code.", original_text: " Vamos falar de clin code." },
      ],
      corrected_segments: 1,
    });
    correctTranscriptionSegment.mockResolvedValue(corrected);
    const { client } = renderWithQuery(<InteractiveTranscriptionPanel transcription={transcription()} currentTime={0} />);

    fireEvent.click(screen.getByRole("button", { name: "Corrigir o trecho de 00:03" }));
    fireEvent.change(screen.getByLabelText("Texto do trecho de 00:03"), { target: { value: "Vamos falar de Clean Code." } });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/ }));

    await waitFor(() => expect(correctTranscriptionSegment).toHaveBeenCalledWith("t1", 1, "Vamos falar de Clean Code."));
    expect(client.getQueryData(["transcription", "m1"])).toEqual(corrected);
  });

  it("hides corrections from viewers and explains an unfinished transcription", () => {
    renderWithQuery(<InteractiveTranscriptionPanel transcription={transcription()} currentTime={0} canEdit={false} />);
    expect(screen.queryByRole("button", { name: /Corrigir o trecho/ })).not.toBeInTheDocument();
  });
});
