import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { MediaRow } from "@/features/media/components/MediaRow";
import { Media, MediaStatus, MediaType } from "@/types";

const post = vi.fn();
vi.mock("@/lib/api", () => ({
  default: { post: (...args: unknown[]) => post(...args), get: vi.fn(), delete: vi.fn() },
  bindSession: vi.fn(),
}));

const media = (status: MediaStatus, extra: Partial<Media> = {}): Media =>
  ({
    id: "m1",
    user_id: "u1",
    filename: "aula.mp4",
    media_type: MediaType.VIDEO,
    status,
    created_at: new Date().toISOString(),
    ...extra,
  }) as Media;

const renderRow = (m: Media) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <ul><MediaRow media={m} /></ul>
      </MemoryRouter>
    </QueryClientProvider>
  );

describe("MediaRow", () => {
  beforeEach(() => post.mockReset());

  it("offers a visible retry, with the reason, only when processing failed", async () => {
    post.mockResolvedValue({ data: { message: "ok" } });
    renderRow(media(MediaStatus.FAILED, { error_message: "Modelo de linguagem indisponível" }));

    // Em linguagem simples; o texto técnico fica na dica (title).
    expect(screen.getByText("O modelo de linguagem não respondeu.")).toHaveAttribute("title", "Modelo de linguagem indisponível");
    fireEvent.click(screen.getByRole("button", { name: /tentar novamente/i }));

    await waitFor(() => expect(post).toHaveBeenCalledWith("/media/m1/reprocess"));
  });

  it.each([MediaStatus.COMPLETED, MediaStatus.PROCESSING, MediaStatus.UPLOADED])(
    "does not offer retry for %s media",
    (status) => {
      renderRow(media(status));
      expect(screen.queryByRole("button", { name: /tentar novamente/i })).not.toBeInTheDocument();
    }
  );
});
