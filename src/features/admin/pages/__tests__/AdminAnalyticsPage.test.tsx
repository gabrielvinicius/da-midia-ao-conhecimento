import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { AdminAnalyticsPage, formatSeconds, taskLabel } from "../AdminAnalyticsPage";

vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ user: { role: "ADMIN" } }) }));

vi.mock("../../hooks/useAdminQueries", () => ({
  useMediaProcessingStats: () => ({
    data: { total_media: 12, completed: 10, failed: 1, processing: 1, uploaded: 0, success_rate: 83.3 },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useProcessingTimes: () => ({
    data: {
      days: 30,
      items: [
        { task_type: "transcription", model_name: "FasterWhisperTranscriber", runs: 3, failures: 0,
          avg_seconds: 95.2, median_seconds: 90, max_seconds: 120, realtime_factor: 0.08 },
        { task_type: "analysis.synthesis", model_name: null, runs: 3, failures: 1,
          avg_seconds: 42.5, median_seconds: 40, max_seconds: 50, realtime_factor: null },
      ],
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

describe("AdminAnalyticsPage", () => {
  it("formats durations and task names", () => {
    expect(formatSeconds(42.5)).toBe("42.5 s");
    expect(formatSeconds(95.2)).toBe("1 min 35 s");
    expect(formatSeconds(null)).toBe("—");
    expect(taskLabel("analysis.synthesis")).toBe("Resumo final");
  });

  it("shows the measured processing times per task", () => {
    render(<AdminAnalyticsPage />);
    expect(screen.getByText("Tempos de processamento")).toBeInTheDocument();
    expect(screen.getByText("Transcrição")).toBeInTheDocument();
    expect(screen.getByText("Resumo final")).toBeInTheDocument();
    expect(screen.getByText("1 min 35 s")).toBeInTheDocument();
    expect(screen.getByText("0.08×")).toBeInTheDocument();
  });
});
