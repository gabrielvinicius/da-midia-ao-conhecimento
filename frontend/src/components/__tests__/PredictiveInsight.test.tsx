import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { PredictiveInsight, formatEstimate } from "@/components/PredictiveInsight";

const get = vi.fn();
vi.mock("@/lib/api", () => ({ default: { get: (...args: unknown[]) => get(...args) } }));

const renderCard = () =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <PredictiveInsight mediaId="m1" isEnabled />
    </QueryClientProvider>
  );

describe("PredictiveInsight", () => {
  beforeEach(() => get.mockReset());

  it("formats the estimate for people", () => {
    expect(formatEstimate(60)).toBe("menos de 2 minutos");
    expect(formatEstimate(540)).toBe("cerca de 9 minutos");
    expect(formatEstimate(2 * 3600 + 600)).toBe("cerca de 2 h 10 min");
  });

  it("shows the estimate measured on this installation", async () => {
    get.mockResolvedValue({ data: { estimated_seconds: 540, media_seconds: 3600, includes_analysis: true } });
    renderCard();
    await waitFor(() => expect(screen.getByText(/cerca de 9 minutos/)).toBeInTheDocument());
    expect(get).toHaveBeenCalledWith("/transcriptions/media/m1/estimate");
  });

  it("shows nothing (and does not crash) while there is no basis to estimate", async () => {
    get.mockResolvedValue({ data: { estimated_seconds: null, media_seconds: null, includes_analysis: false } });
    const { container } = renderCard();
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
