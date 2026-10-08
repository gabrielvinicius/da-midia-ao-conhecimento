import type { Page, Route } from '@playwright/test';

export const USER = { id: 'u1', email: 'ana@exemplo.com', role: 'user', is_active: true };

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

/**
 * API simulada. `loggedIn` diz se o cookie de renovação existe; o login o cria.
 * Devolve os caminhos chamados, para os testes conferirem o que foi pedido.
 */
export const mockApi = async (page: Page, { loggedIn = false } = {}) => {
  const calls: string[] = [];
  let session = loggedIn;

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api/, '');
    calls.push(`${route.request().method()} ${path}`);

    if (path === '/auth/refresh') {
      return session ? json(route, { access_token: 'acesso' }) : json(route, { detail: 'Sessão expirada.' }, 401);
    }
    if (path === '/auth/token') {
      session = true;
      return json(route, { message: 'ok', access_token: 'acesso', token_type: 'bearer' });
    }
    if (path === '/auth/me') return json(route, USER);
    if (path === '/auth/scoped-token') return json(route, { detail: 'Indisponível no teste.' }, 403);
    if (path === '/media/stats') return json(route, { total: 5, by_status: { completed: 5 }, by_type: { video: 5 } });
    if (path === '/media/') return json(route, { items: [], total: 0, page: 1, pages: 0, limit: 10 });
    if (path === '/notifications/') return json(route, []);
    if (path === '/monitoring/system-status') return json(route, { pressure: 'low' });
    return json(route, { detail: 'Não encontrado.' }, 404);
  });

  return calls;
};
