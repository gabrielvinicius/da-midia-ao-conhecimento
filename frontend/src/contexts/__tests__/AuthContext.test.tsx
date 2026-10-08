import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { act, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '../AuthContext';

vi.mock('react-toastify', () => ({ toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() } }));

const calls: string[] = [];
const server = setupServer(
  http.post('/api/auth/refresh', () => {
    calls.push('refresh');
    return new HttpResponse(null, { status: 401 });
  }),
  http.get('/api/auth/me', () => {
    calls.push('me');
    return HttpResponse.json({ id: 'u1', email: 'a@b.c', role: 'user', is_active: true });
  }),
  http.post('/api/auth/logout', () => {
    calls.push('logout');
    return new HttpResponse(null, { status: 204 });
  }),
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  sessionStorage.clear();
  calls.length = 0;
});
afterAll(() => server.close());

const Probe = () => {
  const { user, isLoading, logout } = useAuth();
  if (isLoading) return <p>carregando</p>;
  return (
    <>
      <p>{user ? user.email : 'visitante'}</p>
      <button onClick={logout}>sair</button>
    </>
  );
};

const renderAuth = () =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthProvider><Probe /></AuthProvider>
    </QueryClientProvider>,
  );

describe('AuthProvider', () => {
  it('visitante: tenta renovar uma vez e não pede /auth/me', async () => {
    renderAuth();
    expect(await screen.findByText('visitante')).toBeInTheDocument();
    expect(calls).toEqual(['refresh']);
  });

  it('com token na aba, carrega o usuário sem renovar', async () => {
    sessionStorage.setItem('access_token', 'valido');
    renderAuth();
    expect(await screen.findByText('a@b.c')).toBeInTheDocument();
    expect(calls).toEqual(['me']);
  });

  it('sair revoga no servidor, apaga o token e avisa a aplicação', async () => {
    sessionStorage.setItem('access_token', 'valido');
    const onLogout = vi.fn();
    window.addEventListener('app:logout', onLogout);
    renderAuth();
    await screen.findByText('a@b.c');

    await act(async () => screen.getByText('sair').click());

    await waitFor(() => expect(screen.getByText('visitante')).toBeInTheDocument());
    expect(calls).toContain('logout');
    expect(sessionStorage.getItem('access_token')).toBeNull();
    expect(onLogout).toHaveBeenCalled();
    window.removeEventListener('app:logout', onLogout);
  });
});
