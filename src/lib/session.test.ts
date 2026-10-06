import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { toast } from "react-toastify";
import api from "@/lib/api";
import authService from "@/services/auth.service";

vi.mock("react-toastify", () => ({ toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() } }));

let refreshCalls = 0;
const server = setupServer(
  http.post("/api/auth/refresh", () => {
    refreshCalls += 1;
    return HttpResponse.json({ access_token: `novo-${refreshCalls}` });
  }),
  http.get("/api/protegido/:n", ({ request }) =>
    request.headers.get("Authorization") === "Bearer novo-1"
      ? HttpResponse.json({ ok: true })
      : new HttpResponse(null, { status: 401 }),
  ),
  http.get("/api/auth/me", () => new HttpResponse(null, { status: 401 })),
  http.get("/api/sem-analise", () => HttpResponse.json({ detail: "Análise não encontrada" }, { status: 404 })),
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  sessionStorage.clear();
  refreshCalls = 0;
  vi.mocked(toast.error).mockClear();
});
afterAll(() => server.close());

describe("sessão", () => {
  it("várias requisições com o token vencido fazem uma só renovação", async () => {
    // O token de renovação só vale uma vez: antes, cada 401 pedia o seu e a
    // sessão era apagada a cada 30 minutos.
    sessionStorage.setItem("access_token", "vencido");
    const results = await Promise.all([1, 2, 3].map((n) => api.get(`/protegido/${n}`)));
    expect(results.every((r) => r.data.ok)).toBe(true);
    expect(refreshCalls).toBe(1);
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("visitante sem sessão não recebe 'Sessão expirada'", async () => {
    const logout = vi.fn();
    window.addEventListener("app:logout", logout);
    server.use(http.post("/api/auth/refresh", () => new HttpResponse(null, { status: 401 })));

    expect(await authService.restoreSession()).toBe(false);
    await expect(api.get("/auth/me")).rejects.toBeTruthy();

    expect(toast.error).not.toHaveBeenCalled();
    expect(logout).not.toHaveBeenCalled();
    window.removeEventListener("app:logout", logout);
  });

  it("sessão que não renova acaba com um aviso só", async () => {
    sessionStorage.setItem("access_token", "vencido");
    server.use(http.post("/api/auth/refresh", () => new HttpResponse(null, { status: 401 })));
    await Promise.allSettled([api.get("/protegido/1"), api.get("/protegido/2")]);
    expect(authService.hasSession()).toBe(false);
    expect(toast.error).toHaveBeenCalledWith(expect.stringContaining("Sessão expirada"), expect.anything());
  });

  it("um 404 esperado não gera aviso global", async () => {
    // A tela de uma mídia ainda sem análise mostrava "Não encontrado".
    await expect(api.get("/sem-analise")).rejects.toBeTruthy();
    expect(toast.error).not.toHaveBeenCalled();
  });
});
