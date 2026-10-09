import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { formatElapsed } from "@/lib/processingLabels";
import type { ProcessingQueue } from "../../api";
import { AdminQueuePage } from "../AdminQueuePage";

let queue: Partial<ProcessingQueue> | undefined;

vi.mock("../../hooks/useAdminQueries", () => ({
  useProcessingQueue: () => ({ data: queue, isLoading: false, isError: false, isFetching: false, refetch: vi.fn() }),
}));

const now = new Date().toISOString();
const item = (position: number, status: "uploaded" | "processing" | "analyzing", extra = {}) => ({
  position,
  media_id: `m${position}`,
  filename: `aula${position}.mp4`,
  media_type: "video",
  status,
  owner_email: "ana@exemplo.com",
  created_at: now,
  stage_since: now,
  stage_seconds: 600,
  stuck: false,
  ...extra,
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <AdminQueuePage />
    </MemoryRouter>,
  );

describe("AdminQueuePage", () => {
  it("formata o tempo na etapa", () => {
    expect(formatElapsed(42)).toBe("42 s");
    expect(formatElapsed(600)).toBe("10 min");
    expect(formatElapsed(2 * 3600 + 300)).toBe("2 h 5 min");
    expect(formatElapsed(3 * 86400)).toBe("3 d");
  });

  it("lista a fila na ordem, com dono, etapa e o tempo nela", () => {
    queue = {
      items: [item(1, "analyzing"), item(2, "uploaded")],
      counts: { uploaded: 1, processing: 0, analyzing: 1 },
      broker: { transcription_queue: 3, text_analysis_queue: 0, transcription_fast_lane: 0, celery: 0 },
      truncated: false,
    };
    renderPage();

    const rows = screen.getAllByRole("listitem").filter((li) => li.textContent?.includes("aula"));
    expect(rows.map((r) => within(r).getByLabelText(/Posição/).textContent)).toEqual(["1", "2"]);
    expect(within(rows[0]).getByText("Analisando")).toBeInTheDocument();
    expect(within(rows[0]).getByText("há 10 min")).toBeInTheDocument();
    expect(within(rows[0]).getByText(/ana@exemplo\.com/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /aula1\.mp4/ })).toHaveAttribute("href", "/media/m1");
    // Tarefas esperando no Celery, por fila.
    expect(screen.getByText("Transcrição").nextSibling?.textContent).toBe("3");
    expect(screen.queryByText("Parece parada")).not.toBeInTheDocument();
  });

  it("destaca as mídias paradas e avisa no topo", () => {
    queue = {
      items: [item(1, "uploaded", { stuck: true, stage_seconds: 3600 })],
      counts: { uploaded: 1, processing: 0, analyzing: 0 },
      broker: null,
      truncated: false,
    };
    renderPage();

    expect(screen.getByText("Parece parada")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("1 mídia está na mesma etapa");
    expect(screen.getByText("Não foi possível ler as filas no Redis.")).toBeInTheDocument();
  });

  it("fila vazia", () => {
    queue = { items: [], counts: { uploaded: 0, processing: 0, analyzing: 0 }, broker: {}, truncated: false };
    renderPage();
    expect(screen.getByText("Nenhuma mídia na fila: tudo processado.")).toBeInTheDocument();
  });
});
