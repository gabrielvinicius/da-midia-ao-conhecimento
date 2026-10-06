import { describe, expect, it } from "vitest";
import { bulkReprocessMessage } from "../index";

describe("bulkReprocessMessage", () => {
  it("avisa quando ainda há falhas para o próximo lote", () => {
    expect(bulkReprocessMessage({ reprocessed_count: 50, failed_count: 0, more_pending: true })).toBe(
      "50 mídia(s) enviada(s) para reprocessamento. Há mais mídias com falha: clique de novo para o próximo lote.",
    );
  });

  it("informa as que não puderam ser reenviadas", () => {
    expect(bulkReprocessMessage({ reprocessed_count: 2, failed_count: 1, more_pending: false })).toBe(
      "2 mídia(s) enviada(s) para reprocessamento. 1 não puderam ser reenviadas.",
    );
  });
});
