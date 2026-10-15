import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import SearchPage, { formatTimestamp } from "@/pages/SearchPage";

const get = vi.fn();
vi.mock("@/lib/api", () => ({ default: { get: (...args: unknown[]) => get(...args) } }));

const RESULTS = [
  { media_id: "m1", content: "A regra da cadeia deriva funções compostas.", relevance: 82.4, start: 754, end: 790, title: "Derivadas", match: "strong" },
  { media_id: "m2", content: "Outro exemplo com a cadeia de funções.", relevance: 30, start: 60, end: 90, title: null, match: "related" },
  { media_id: "m1", content: "Revisão da regra no fim da aula.", relevance: 20, start: 1500, end: 1530, title: "Derivadas", match: "related" },
];

const respond = (results: unknown[]) =>
  get.mockImplementation((url: string) =>
    url === "/text-analysis/search"
      ? Promise.resolve({ data: results })
      : Promise.resolve({ data: { id: url.split("/").pop(), filename: `${url.split("/").pop()}.mp4`, media_type: "video" } }),
  );

const renderPage = (path = "/busca") =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[path]}>
        <SearchPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe("formatTimestamp", () => {
  it("formats seconds as mm:ss or h:mm:ss", () => {
    expect(formatTimestamp(75)).toBe("01:15");
    expect(formatTimestamp(3725)).toBe("1:02:05");
    expect(formatTimestamp(null)).toBeNull();
  });
});

describe("SearchPage", () => {
  beforeEach(() => {
    get.mockReset();
    localStorage.clear();
  });

  it("groups the passages by media, with the title, the time and a link to the moment", async () => {
    respond(RESULTS);
    renderPage();

    fireEvent.change(screen.getByLabelText("Pergunta"), { target: { value: "regra da cadeia" } });
    fireEvent.click(screen.getByRole("button", { name: /buscar/i }));

    await waitFor(() => expect(screen.getByText("3 trechos em 2 mídias")).toBeInTheDocument());
    expect(get).toHaveBeenCalledWith("/text-analysis/search", { params: { query: "regra da cadeia", limit: 20 } });

    const first = screen.getByRole("link", { name: "Derivadas" }).closest("article")!;
    expect(within(first).getAllByRole("listitem")).toHaveLength(2);
    expect(within(first).getByText("Trata disso")).toBeInTheDocument();
    expect(within(first).getByText(/12:34/)).toBeInTheDocument();
    expect(within(first).getAllByRole("link", { name: /Abrir neste momento/ })[0]).toHaveAttribute(
      "href",
      "/media/m1?t=754&aba=transcricao",
    );
    // Sem título do resumo, vale o nome do arquivo.
    await waitFor(() => expect(screen.getByRole("link", { name: "m2.mp4" })).toBeInTheDocument());
    // As palavras da pergunta ficam destacadas no trecho.
    expect(within(first).getAllByText("regra")[0].tagName).toBe("MARK");
  });

  it("says when nothing in the media is about the question", async () => {
    respond([]);
    renderPage("/busca?q=receita%20de%20bolo");
    await waitFor(() => expect(screen.getByText("Nenhum trecho das suas mídias trata disso.")).toBeInTheDocument());
  });

  it("warns when no passage clearly answers, but still lists the closest ones", async () => {
    respond([{ ...RESULTS[0], relevance: 1.3, match: "unrecognized" }]);
    renderPage("/busca?q=ordem%20dos%20fatores");
    await waitFor(() => expect(screen.getByText("Nenhum trecho trata claramente disso.")).toBeInTheDocument());
    expect(screen.getByText("Pouca relação")).toBeInTheDocument();
    expect(screen.getByText(/funções compostas/)).toBeInTheDocument();
  });

  it("remembers recent searches and offers examples before searching", async () => {
    respond(RESULTS);
    renderPage();
    expect(screen.getByText("Como buscar")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Quem escreveu o manifesto ágil?" }));
    await waitFor(() => expect(get).toHaveBeenCalledWith("/text-analysis/search", expect.anything()));
    expect(JSON.parse(localStorage.getItem("busca-recentes")!)).toEqual(["Quem escreveu o manifesto ágil?"]);
  });

  it("shows in the field the search from the address, and follows it when it changes", async () => {
    respond(RESULTS);
    renderPage("/busca?q=regra%20da%20cadeia");
    expect(screen.getByLabelText("Pergunta")).toHaveValue("regra da cadeia");
    cleanup();

    // O exemplo só muda o endereço; o campo vem dele.
    renderPage();
    expect(screen.getByLabelText("Pergunta")).toHaveValue("");
    fireEvent.click(screen.getByRole("button", { name: "Quem escreveu o manifesto ágil?" }));
    await waitFor(() => expect(screen.getByLabelText("Pergunta")).toHaveValue("Quem escreveu o manifesto ágil?"));
  });

  it("does not search with fewer than 3 characters", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Pergunta"), { target: { value: "ab" } });
    expect(screen.getByRole("button", { name: /buscar/i })).toBeDisabled();
    expect(get).not.toHaveBeenCalled();
  });
});
