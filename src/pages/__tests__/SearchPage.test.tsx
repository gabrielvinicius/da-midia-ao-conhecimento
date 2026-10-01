import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import SearchPage, { formatTimestamp } from "@/pages/SearchPage";

const get = vi.fn();
vi.mock("@/lib/api", () => ({ default: { get: (...args: unknown[]) => get(...args) } }));

const renderPage = () =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <SearchPage />
      </MemoryRouter>
    </QueryClientProvider>
  );

describe("formatTimestamp", () => {
  it("formats seconds as mm:ss or h:mm:ss", () => {
    expect(formatTimestamp(75)).toBe("01:15");
    expect(formatTimestamp(3725)).toBe("1:02:05");
    expect(formatTimestamp(null)).toBeNull();
  });
});

describe("SearchPage", () => {
  beforeEach(() => get.mockReset());

  it("searches and shows the passage with its time and a link to the media", async () => {
    get.mockResolvedValue({
      data: [{ media_id: "m1", content: "A regra da cadeia deriva funções compostas.", relevance: 82.4, start: 754, end: 790 }],
    });
    renderPage();

    fireEvent.change(screen.getByLabelText("Pergunta"), { target: { value: "regra da cadeia" } });
    fireEvent.click(screen.getByRole("button", { name: /buscar/i }));

    await waitFor(() => expect(screen.getByText(/funções compostas/)).toBeInTheDocument());
    expect(get).toHaveBeenCalledWith("/text-analysis/search", { params: { query: "regra da cadeia", limit: 10 } });
    expect(screen.getByText("Trecho em 12:34 – 13:10")).toBeInTheDocument();
    expect(screen.getByText("82% de relevância")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /abrir no trecho/i })).toHaveAttribute("href", "/media/m1?t=754");
  });

  it("does not search with fewer than 3 characters", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Pergunta"), { target: { value: "ab" } });
    expect(screen.getByRole("button", { name: /buscar/i })).toBeDisabled();
    expect(get).not.toHaveBeenCalled();
  });
});
