import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { MediaCard } from "@/features/media/components/MediaCard";
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

const renderCard = (m: Media) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <MediaCard media={m} />
      </MemoryRouter>
    </QueryClientProvider>
  );

describe("MediaCard", () => {
  beforeEach(() => post.mockReset());

  it("offers a visible retry, with the reason, only when processing failed", async () => {
    post.mockResolvedValue({ data: { message: "ok" } });
    renderCard(media(MediaStatus.FAILED, { error_message: "Modelo de linguagem indisponível" }));

    expect(screen.getByText("Modelo de linguagem indisponível")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /tentar novamente/i }));

    await waitFor(() => expect(post).toHaveBeenCalledWith("/media/m1/reprocess"));
  });

  it.each([MediaStatus.COMPLETED, MediaStatus.PROCESSING, MediaStatus.UPLOADED])(
    "does not offer retry for %s media",
    (status) => {
      renderCard(media(status));
      expect(screen.queryByRole("button", { name: /tentar novamente/i })).not.toBeInTheDocument();
    }
  );
});
